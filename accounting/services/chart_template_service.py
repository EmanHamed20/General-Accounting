from django.db import transaction

from accounting.models import Account, AccountGroup, AccountGroupTemplate, AccountTemplate, Company, Country


def apply_chart_template_to_company(*, company: Company, country: Country) -> dict:
    """Apply country chart templates into a company chart of accounts.

    The operation is idempotent by natural keys:
    - groups: (company, code_prefix_start, code_prefix_end)
    - accounts: (company, code)
    """

    groups_created = 0
    groups_updated = 0
    accounts_created = 0
    accounts_updated = 0

    with transaction.atomic():
        template_groups = list(
            AccountGroupTemplate.objects.filter(country=country)
            .select_related("parent")
            .order_by("parent_id", "code_prefix_start", "id")
        )

        template_group_to_group = {}
        pending = template_groups[:]

        while pending:
            next_pending = []
            progressed = False

            for template_group in pending:
                if template_group.parent_id and template_group.parent_id not in template_group_to_group:
                    next_pending.append(template_group)
                    continue

                parent = template_group_to_group.get(template_group.parent_id)
                group, created = AccountGroup.objects.update_or_create(
                    company=company,
                    code_prefix_start=template_group.code_prefix_start,
                    code_prefix_end=template_group.code_prefix_end,
                    defaults={
                        "name": template_group.name,
                        "parent": parent,
                    },
                )
                template_group_to_group[template_group.id] = group
                progressed = True

                if created:
                    groups_created += 1
                else:
                    groups_updated += 1

            if not progressed:
                unresolved_ids = ", ".join(str(item.id) for item in next_pending)
                raise ValueError(
                    f"Could not resolve template group parent tree for country={country.code}. "
                    f"Unresolved template IDs: {unresolved_ids}"
                )

            pending = next_pending

        for template_account in AccountTemplate.objects.filter(country=country).select_related("group").order_by("code"):
            group = template_group_to_group.get(template_account.group_id)
            account, created = Account.objects.update_or_create(
                company=company,
                code=template_account.code,
                defaults={
                    "group": group,
                    "name": template_account.name,
                    "account_type": template_account.account_type,
                    "reconcile": template_account.reconcile,
                    "deprecated": template_account.deprecated,
                },
            )

            if created:
                accounts_created += 1
            else:
                accounts_updated += 1

    return {
        "company_id": company.id,
        "country_id": country.id,
        "groups_created": groups_created,
        "groups_updated": groups_updated,
        "accounts_created": accounts_created,
        "accounts_updated": accounts_updated,
    }
