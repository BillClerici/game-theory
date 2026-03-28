from apps.users.models import SocialAccount
from rest_framework_simplejwt.tokens import RefreshToken


def save_social_account(backend, user, response, *args, **kwargs):
    """Persist or update the SocialAccount record for this login."""
    provider = backend.name
    uid = kwargs.get('uid', '')
    SocialAccount.objects.update_or_create(
        provider=provider,
        provider_uid=uid,
        defaults={
            'user': user,
            'raw_data': response,
            'access_token': kwargs.get('access_token', ''),
        }
    )
    user.last_login_provider = provider
    update_fields = ['last_login_provider', 'updated_at']

    # Set defaults on first login (when app_role is not yet assigned)
    if not user.app_role_id:
        from apps.lookup.models import LookupValue
        try:
            role_parent = LookupValue.objects.get(parent__isnull=True, code='USER_ROLE')
            user.app_role = LookupValue.objects.get(parent=role_parent, code='ANALYST')
            update_fields.append('app_role_id')
        except LookupValue.DoesNotExist:
            pass

    if not user.subscription_tier_id:
        from apps.lookup.models import LookupValue
        try:
            tier_parent = LookupValue.objects.get(parent__isnull=True, code='SUBSCRIPTION_TIER')
            user.subscription_tier = LookupValue.objects.get(parent=tier_parent, code='FREE')
            update_fields.append('subscription_tier_id')
        except LookupValue.DoesNotExist:
            pass

    user.save(update_fields=update_fields)


def issue_jwt(strategy, backend, user, *args, **kwargs):
    """Issue JWT tokens and store them in the session for the callback view to pick up."""
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)
    # Store tokens in session — the auth_callback view (or template context) will use them
    strategy.request.session['jwt_access'] = access_token
    strategy.request.session['jwt_refresh'] = refresh_token
