from django.conf import settings as django_settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import permissions, viewsets
from rest_framework.decorators import action

from accounting.models import UserCompanyAccess

from .shared import *


class SessionViewSet(viewsets.ViewSet):
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
            allowed_companies_qs = access.allowed_companies.all().order_by("name")
        elif company:
            allowed_companies_qs = Company.objects.filter(id=company.id).order_by("name")
        else:
            allowed_companies_qs = Company.objects.none()
        allowed_companies = [
            {"id": c.id, "name": c.name, "code": c.code}
            for c in allowed_companies_qs
        ]
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
                "allowed_companies": allowed_companies,
                "disallowed_ancestor_companies": [],
            },
        }

    @action(detail=False, methods=["post"], url_path="authenticate", permission_classes=[permissions.AllowAny])
    def authenticate_session(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        if not username or not password:
            return Response(
                {"detail": "username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=username, password=password)
        if not user:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response({"detail": "User is inactive."}, status=status.HTTP_403_FORBIDDEN)

        login(request, user)
        return Response(self._build_session_info(request, user), status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="signup", permission_classes=[permissions.AllowAny])
    def signup(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password")
        email = (request.data.get("email") or "").strip()
        first_name = (request.data.get("first_name") or "").strip()
        last_name = (request.data.get("last_name") or "").strip()
        company_name_raw = (request.data.get("company_name") or "").strip()
        country_id = request.data.get("country_id")
        currency_id = request.data.get("currency_id")

        if not username:
            return Response({"username": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({"password": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not company_name_raw:
            return Response({"company_name": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

        UserModel = get_user_model()
        if UserModel.objects.filter(username=username).exists():
            return Response({"username": "Username already exists."}, status=status.HTTP_400_BAD_REQUEST)
        if email and UserModel.objects.filter(email=email).exists():
            return Response({"email": "Email already exists."}, status=status.HTTP_400_BAD_REQUEST)

        country = None
        if country_id is not None:
            country = Country.objects.filter(id=country_id).first()
            if not country:
                return Response({"country_id": "Country not found."}, status=status.HTTP_400_BAD_REQUEST)

        currency = None
        if currency_id is not None:
            currency = Currency.objects.filter(id=currency_id).first()
            if not currency:
                return Response({"currency_id": "Currency not found."}, status=status.HTTP_400_BAD_REQUEST)

        company_name = self._generate_unique_company_name(company_name_raw)
        company_code = self._generate_unique_company_code(company_name)

        with transaction.atomic():
            user = UserModel.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            company = Company.objects.create(
                name=company_name,
                code=company_code,
                legal_name=company_name,
                country=country,
            )
            access = UserCompanyAccess.objects.create(
                user=user,
                current_company=company,
            )
            access.allowed_companies.add(company)

            if not currency and country:
                default_country_currency = (
                    CountryCurrency.objects.select_related("currency")
                    .filter(country_id=country.id, is_default=True, active=True)
                    .first()
                )
                if default_country_currency:
                    currency = default_country_currency.currency

            AccountingSettings.objects.create(
                company=company,
                country_code=(country.code if country else ""),
                fiscal_localization_country=country,
                chart_template_country=country,
                account_fiscal_country=country,
                currency=currency,
            )

        login(request, user)
        return Response(self._build_session_info(request, user), status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="get-session-info")
    def get_session_info(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(self._build_session_info(request, request.user), status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="switch-company")
    def switch_company(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        company_id = request.data.get("company_id")
        if not company_id:
            return Response({"company_id": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

        access, _ = UserCompanyAccess.objects.get_or_create(user=request.user)
        if not access.allowed_companies.filter(id=company_id).exists():
            return Response(
                {"company_id": "This company is not allowed for current user."},
                status=status.HTTP_403_FORBIDDEN,
            )

        access.current_company_id = company_id
        access.save(update_fields=["current_company", "updated_at"])
        return Response(self._build_session_info(request, request.user), status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="logout")
    def logout_session(self, request):
        if request.user and request.user.is_authenticated:
            logout(request)
        return Response({"detail": "Logged out."}, status=status.HTTP_200_OK)
