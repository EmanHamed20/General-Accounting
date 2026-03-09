from django.conf import settings as django_settings
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounting.models import UserCompanyAccess

from .shared import *


class SessionViewSet(viewsets.ViewSet):
    def _build_auth_response(self, request, user):
        refresh = RefreshToken.for_user(user)
        payload = self._build_session_info(request, user)
        payload["tokens"] = {
            "access": str(refresh.access_token),
        }
        return payload, str(refresh)

    

    # def _set_refresh_cookie(self, response, refresh_token):
    #     response.set_cookie(
    #         key="refresh_token",
    #         value=refresh_token,
    #         httponly=True,
    #         # secure=not django_settings.DEBUG,
    #         # samesite=self._refresh_cookie_samesite(),
    #          secure=False,        # False for local dev (no HTTPS)
    #     samesite="None",     # Required for cross-origin
    #         path="/api/session/",
    #         max_age=7 * 24 * 60 * 60,
    #     )
    def _refresh_cookie_samesite(self):
       return "Lax" if django_settings.DEBUG else "None"
    
    def _set_refresh_cookie(self, response, refresh_token):
      is_debug = django_settings.DEBUG
      response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure= False,                 # False in dev
        # samesite="Lax" if is_debug else "None",
       samesite = "Lax",
        path="/api/session/",
        max_age=7 * 24 * 60 * 60,
    )


    def _clear_refresh_cookie(self, response):
        response.delete_cookie(
            key="refresh_token",
            path="/api/session/",
            # samesite=self._refresh_cookie_samesite(),
             samesite = "Lax",

        )

    def _generate_unique_company_name(self, base_name):
        name = (base_name or "").strip()
        if not name:
            name = "New Company"
        if not Company.objects.filter(name=name).exists():
            return name
        index = 2
        while True:
            candidate = f"{name} {index}"
            if not Company.objects.filter(name=candidate).exists():
                return candidate
            index += 1

    def _generate_unique_company_code(self, company_name):
        normalized = "".join(ch for ch in (company_name or "").upper() if ch.isalnum())
        base = (normalized[:8] or "COMP")
        code = base
        index = 1
        while Company.objects.filter(code=code).exists():
            suffix = str(index)
            code = f"{base[: max(1, 8 - len(suffix))]}{suffix}"
            index += 1
        return code

    def _resolve_access(self, user):
        return UserCompanyAccess.objects.select_related("current_company", "current_company__country").filter(
            user_id=user.id
        ).first()

    def _resolve_company(self, request, user):
        access = self._resolve_access(user)
        if access:
            if access.current_company_id:
                return access.current_company
            first_active = access.active_companies.select_related("country").order_by("id").first()
            if first_active:
                return first_active
            first_allowed = access.allowed_companies.select_related("country").order_by("id").first()
            if first_allowed:
                return first_allowed

        if hasattr(user, "company_id") and user.company_id:
            return Company.objects.select_related("country").filter(id=user.company_id).first()
        if hasattr(user, "company") and getattr(user, "company", None):
            return Company.objects.select_related("country").filter(id=user.company.id).first()

        header_company_id = request.headers.get("X-Company-Id")
        if header_company_id:
            return Company.objects.select_related("country").filter(id=header_company_id).first()

        if Company.objects.count() == 1:
            return Company.objects.select_related("country").first()
        return None

    def _build_session_info(self, request, user):
        company = self._resolve_company(request, user)
        access = self._resolve_access(user)
        settings_obj = None
        settings_currency = None
        default_country_currency = None

        if company:
            settings_obj = (
                AccountingSettings.objects.select_related("currency")
                .filter(company_id=company.id)
                .first()
            )
            settings_currency = settings_obj.currency if settings_obj and settings_obj.currency_id else None
            if company.country_id:
                default_country_currency = (
                    CountryCurrency.objects.select_related("currency")
                    .filter(country_id=company.country_id, is_default=True, active=True)
                    .first()
                )

        effective_currency = settings_currency or (
            default_country_currency.currency if default_country_currency else None
        )

        if access:
            allowed_companies_qs = access.allowed_companies.select_related("country").all().order_by("name")
            active_company_ids = set(access.active_companies.values_list("id", flat=True))
        elif company:
            allowed_companies_qs = Company.objects.select_related("country").filter(id=company.id).order_by("name")
            active_company_ids = {company.id}
        else:
            allowed_companies_qs = Company.objects.none()
            active_company_ids = set()
        allowed_companies = [
            {
                "id": c.id,
                "name": c.name,
                "code": c.code,
                "country": (
                    {
                        "id": c.country.id,
                        "code": c.country.code,
                        "name": c.country.name,
                    }
                    if c.country_id
                    else None
                ),
                "is_active": c.id in active_company_ids,
            }
            for c in allowed_companies_qs
        ]
        active_companies = [c for c in allowed_companies if c["is_active"]]
        current_company = None
        if company:
            current_company = next((c for c in allowed_companies if c["id"] == company.id), None)

        return {
            "uid": user.id,
            "name": user.get_full_name() or user.get_username(),
            "username": user.get_username(),
            "user_context": {
                "lang": getattr(user, "lang", "en_US"),
                "tz": getattr(user, "tz", "UTC"),
            },
            "db": str(django_settings.DATABASES["default"]["NAME"]),
            "company": (
                {
                    "id": company.id,
                    "name": company.name,
                    "code": company.code,
                    "country": (
                        {
                            "id": company.country.id,
                            "code": company.country.code,
                            "name": company.country.name,
                        }
                        if company.country_id
                        else None
                    ),
                    "currency": (
                        {
                            "id": effective_currency.id,
                            "code": effective_currency.code,
                            "name": effective_currency.name,
                            "symbol": effective_currency.symbol,
                        }
                        if effective_currency
                        else None
                    ),
                }
                if company
                else None
            ),
            "settings": AccountingSettingsSerializer(settings_obj).data if settings_obj else None,
            "user_companies": {
                "current_company": current_company,
                "active_companies": active_companies,
                "allowed_companies": allowed_companies,
                "disallowed_ancestor_companies": [],
            },
        }

    def _resolve_country_and_currency(self, country_id, currency_id):
        country = None
        if country_id is not None:
            country = Country.objects.filter(id=country_id).first()
            if not country:
                raise DRFValidationError({"country_id": "Country not found."})

        currency = None
        if currency_id is not None:
            currency = Currency.objects.filter(id=currency_id).first()
            if not currency:
                raise DRFValidationError({"currency_id": "Currency not found."})

        if not currency and country:
            default_country_currency = (
                CountryCurrency.objects.select_related("currency")
                .filter(country_id=country.id, is_default=True, active=True)
                .first()
            )
            if default_country_currency:
                currency = default_country_currency.currency

        return country, currency

    def _create_signup_company(self, company_data):
        company_name_raw = (company_data.get("name") or "").strip()
        if not company_name_raw:
            raise DRFValidationError({"companies": "Each company requires a non-empty name."})

        country, currency = self._resolve_country_and_currency(
            company_data.get("country_id"),
            company_data.get("currency_id"),
        )

        company_name = self._generate_unique_company_name(company_name_raw)
        company_code = self._generate_unique_company_code(company_name)

        company = Company.objects.create(
            name=company_name,
            code=company_code,
            legal_name=company_name,
            country=country,
        )

        AccountingSettings.objects.create(
            company=company,
            country_code=(country.code if country else ""),
            fiscal_localization_country=country,
            chart_template_country=country,
            account_fiscal_country=country,
            currency=currency,
        )
        return company

    def _normalize_company_ids(self, company_ids):
        if not isinstance(company_ids, list) or not company_ids:
            raise DRFValidationError({"company_ids": "Must be a non-empty list."})

        normalized_ids = []
        for raw in company_ids:
            try:
                value = int(raw)
            except (TypeError, ValueError) as exc:
                raise DRFValidationError({"company_ids": f"Invalid company id: {raw}"}) from exc
            if value not in normalized_ids:
                normalized_ids.append(value)
        return normalized_ids

    def _resolve_request_user(self, request):
        # Dev fallback: allow APIs to work without login/token by resolving a user context.
        if getattr(request, "user", None) and request.user.is_authenticated:
            return request.user

        payload = request.data if hasattr(request, "data") and isinstance(request.data, dict) else {}
        explicit_user_id = payload.get("user_id") or request.query_params.get("user_id") or request.headers.get("X-User-Id")

        UserModel = get_user_model()
        if explicit_user_id not in (None, ""):
            try:
                explicit_user_id = int(explicit_user_id)
            except (TypeError, ValueError):
                return None
            return UserModel.objects.filter(id=explicit_user_id, is_active=True).first()

        return UserModel.objects.filter(is_active=True).order_by("id").first()

    @action(detail=False, methods=["post"], url_path="authenticate", permission_classes=[permissions.AllowAny])
    def authenticate_session(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password")
        errors = {}
        if not username:
            errors["username"] = "Username is required."
        if not password:
            errors["password"] = "Password is required."
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=username, password=password)
        if not user:
            UserModel = get_user_model()
            if not UserModel.objects.filter(username=username).exists():
                return Response({"username": "Username not found."}, status=status.HTTP_401_UNAUTHORIZED)
            return Response({"password": "Incorrect password."}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response(
                {"detail": "User is inactive. Please contact administrator."},
                status=status.HTTP_403_FORBIDDEN,
            )

        payload, refresh_token = self._build_auth_response(request, user)
        response = Response(payload, status=status.HTTP_200_OK)
        self._set_refresh_cookie(response, refresh_token)
        return response

    @action(detail=False, methods=["post"], url_path="signup", permission_classes=[permissions.AllowAny])
    def signup(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password")
        email = (request.data.get("email") or "").strip()
        first_name = (request.data.get("first_name") or "").strip()
        last_name = (request.data.get("last_name") or "").strip()
        companies_payload = request.data.get("companies")

        if not username:
            return Response({"username": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({"password": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

        UserModel = get_user_model()
        if UserModel.objects.filter(username=username).exists():
            return Response({"username": "Username already exists."}, status=status.HTTP_400_BAD_REQUEST)
        if email and UserModel.objects.filter(email=email).exists():
            return Response({"email": "Email already exists."}, status=status.HTTP_400_BAD_REQUEST)

        if companies_payload is None:
            company_name_raw = (request.data.get("company_name") or "").strip()
            if not company_name_raw:
                return Response(
                    {"companies": "Provide companies list, or legacy company_name field."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            companies_payload = [
                {
                    "name": company_name_raw,
                    "country_id": request.data.get("country_id"),
                    "currency_id": request.data.get("currency_id"),
                    "is_active": True,
                }
            ]

        if not isinstance(companies_payload, list) or not companies_payload:
            return Response({"companies": "Must be a non-empty list."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = UserModel.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

            created_companies = []
            active_companies = []
            for item in companies_payload:
                if not isinstance(item, dict):
                    raise DRFValidationError({"companies": "Each item must be an object."})
                company = self._create_signup_company(item)
                created_companies.append(company)
                if item.get("is_active", True):
                    active_companies.append(company)

            if not created_companies:
                raise DRFValidationError({"companies": "At least one company is required."})
            if not active_companies:
                active_companies = [created_companies[0]]

            current_company = active_companies[0]
            access = UserCompanyAccess.objects.create(
                user=user,
                current_company=current_company,
            )
            access.allowed_companies.set(created_companies)
            access.active_companies.set(active_companies)

        payload, refresh_token = self._build_auth_response(request, user)
        response = Response(payload, status=status.HTTP_201_CREATED)
        self._set_refresh_cookie(response, refresh_token)
        return response

    @action(detail=False, methods=["post"], url_path="refresh", permission_classes=[permissions.AllowAny])
    def refresh(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response({"refresh": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            old_refresh = RefreshToken(refresh_token)
        except TokenError:
            return Response({"detail": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)

        user_id = old_refresh.get("user_id")
        UserModel = get_user_model()
        user = UserModel.objects.filter(id=user_id, is_active=True).first()
        if not user:
            return Response({"detail": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            old_refresh.blacklist()
        except Exception:
            # Blacklist app can be optional in some local environments.
            pass

        new_refresh = RefreshToken.for_user(user)
        response = Response(
            {"tokens": {"access": str(new_refresh.access_token)}},
            status=status.HTTP_200_OK,
        )
        self._set_refresh_cookie(response, str(new_refresh))
        return response

    @action(detail=False, methods=["get"], url_path="get-session-info")
    def get_session_info(self, request):
        # if not request.user or not request.user.is_authenticated:
        #     return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        user = self._resolve_request_user(request)
        if not user:
            return Response({"detail": "No active user available."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(self._build_session_info(request, user), status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="switch-company")
    def switch_company(self, request):
        # if not request.user or not request.user.is_authenticated:
        #     return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        user = self._resolve_request_user(request)
        if not user:
            return Response({"detail": "No active user available."}, status=status.HTTP_401_UNAUTHORIZED)

        company_id = request.data.get("company_id")
        if not company_id:
            return Response({"company_id": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

        access, _ = UserCompanyAccess.objects.get_or_create(user=user)
        if not access.allowed_companies.filter(id=company_id).exists():
            return Response(
                {"company_id": "This company is not allowed for current user."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not access.active_companies.filter(id=company_id).exists():
            access.active_companies.add(company_id)
        access.current_company_id = company_id
        access.save(update_fields=["current_company", "updated_at"])
        return Response(self._build_session_info(request, user), status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="set-active-companies")
    def set_active_companies(self, request):
        # if not request.user or not request.user.is_authenticated:
        #     return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        user = self._resolve_request_user(request)
        if not user:
            return Response({"detail": "No active user available."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            normalized_ids = self._normalize_company_ids(request.data.get("company_ids"))
        except DRFValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        access, _ = UserCompanyAccess.objects.get_or_create(user=user)
        allowed_ids = set(access.allowed_companies.values_list("id", flat=True))
        invalid = [cid for cid in normalized_ids if cid not in allowed_ids]
        if invalid:
            return Response(
                {"company_ids": f"Not allowed for current user: {invalid}"},
                status=status.HTTP_403_FORBIDDEN,
            )

        access.active_companies.set(normalized_ids)
        if not access.current_company_id or access.current_company_id not in normalized_ids:
            access.current_company_id = normalized_ids[0]
            access.save(update_fields=["current_company", "updated_at"])
        return Response(self._build_session_info(request, user), status=status.HTTP_200_OK)

    @action(detail=False, methods=["patch"], url_path="update-profile")
    def update_profile(self, request):
        # if not request.user or not request.user.is_authenticated:
        #     return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        user = self._resolve_request_user(request)
        if not user:
            return Response({"detail": "No active user available."}, status=status.HTTP_401_UNAUTHORIZED)
        payload = request.data if isinstance(request.data, dict) else {}
        allowed_fields = {"first_name", "last_name", "email", "password", "username"}
        changed = False

        UserModel = get_user_model()

        if "username" in payload:
            username = (payload.get("username") or "").strip()
            if not username:
                return Response({"username": "Username cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
            if UserModel.objects.exclude(id=user.id).filter(username=username).exists():
                return Response({"username": "Username already exists."}, status=status.HTTP_400_BAD_REQUEST)
            user.username = username
            changed = True

        if "email" in payload:
            email = (payload.get("email") or "").strip()
            if email and UserModel.objects.exclude(id=user.id).filter(email=email).exists():
                return Response({"email": "Email already exists."}, status=status.HTTP_400_BAD_REQUEST)
            user.email = email
            changed = True

        if "first_name" in payload:
            user.first_name = (payload.get("first_name") or "").strip()
            changed = True
        if "last_name" in payload:
            user.last_name = (payload.get("last_name") or "").strip()
            changed = True
        if "password" in payload:
            password = payload.get("password")
            if not password:
                return Response({"password": "Password cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(password)
            changed = True

        access, _ = UserCompanyAccess.objects.get_or_create(user=user)

        if "company_ids" in payload:
            try:
                normalized_ids = self._normalize_company_ids(payload.get("company_ids"))
            except DRFValidationError as exc:
                return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

            allowed_ids = set(access.allowed_companies.values_list("id", flat=True))
            invalid = [cid for cid in normalized_ids if cid not in allowed_ids]
            if invalid:
                return Response(
                    {"company_ids": f"Not allowed for current user: {invalid}"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            access.active_companies.set(normalized_ids)
            if not access.current_company_id or access.current_company_id not in normalized_ids:
                access.current_company_id = normalized_ids[0]
                access.save(update_fields=["current_company", "updated_at"])

        if "current_company_id" in payload:
            current_company_id = payload.get("current_company_id")
            if not current_company_id:
                return Response({"current_company_id": "This field cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                current_company_id = int(current_company_id)
            except (TypeError, ValueError):
                return Response({"current_company_id": "Must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
            if not access.allowed_companies.filter(id=current_company_id).exists():
                return Response(
                    {"current_company_id": "This company is not allowed for current user."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if not access.active_companies.filter(id=current_company_id).exists():
                access.active_companies.add(current_company_id)
            access.current_company_id = current_company_id
            access.save(update_fields=["current_company", "updated_at"])

        if changed:
            update_fields = [f for f in allowed_fields if f in payload and f != "password"]
            if "password" in payload:
                user.save()
            elif update_fields:
                user.save(update_fields=update_fields)
            else:
                user.save()

        return Response(self._build_session_info(request, user), status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="add-company")
    def add_company(self, request):
        # if not request.user or not request.user.is_authenticated:
        #     return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        user = self._resolve_request_user(request)
        if not user:
            return Response({"detail": "No active user available."}, status=status.HTTP_401_UNAUTHORIZED)

        company_data = request.data if isinstance(request.data, dict) else {}
        if not (company_data.get("name") or "").strip():
            return Response({"name": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            company = self._create_signup_company(company_data)
            access, _ = UserCompanyAccess.objects.get_or_create(user=user)
            access.allowed_companies.add(company)

            make_active = company_data.get("is_active", True)
            if make_active:
                access.active_companies.add(company)
            if company_data.get("set_current", False) or not access.current_company_id:
                if not access.active_companies.filter(id=company.id).exists():
                    access.active_companies.add(company)
                access.current_company = company
                access.save(update_fields=["current_company", "updated_at"])

        return Response(self._build_session_info(request, user), status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="attach-existing-company")
    def attach_existing_company(self, request):
        # if not request.user or not request.user.is_authenticated:
        #     return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        user = self._resolve_request_user(request)
        if not user:
            return Response({"detail": "No active user available."}, status=status.HTTP_401_UNAUTHORIZED)

        company_id = request.data.get("company_id")
        if not company_id:
            return Response({"company_id": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            company_id = int(company_id)
        except (TypeError, ValueError):
            return Response({"company_id": "Must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        company = Company.objects.filter(id=company_id).first()
        if not company:
            return Response({"company_id": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        access, _ = UserCompanyAccess.objects.get_or_create(user=user)
        access.allowed_companies.add(company)

        if request.data.get("is_active", True):
            access.active_companies.add(company)
        if request.data.get("set_current", False) or not access.current_company_id:
            if not access.active_companies.filter(id=company.id).exists():
                access.active_companies.add(company)
            access.current_company = company
            access.save(update_fields=["current_company", "updated_at"])

        return Response(self._build_session_info(request, user), status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="logout", permission_classes=[permissions.AllowAny])
    def logout_session(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except Exception:
                pass
        response = Response({"detail": "Logged out."}, status=status.HTTP_200_OK)
        self._clear_refresh_cookie(response)
        return response
