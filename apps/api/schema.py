import strawberry
import uuid
from typing import Optional, List
from strawberry import auto
from strawberry.types import Info
# Permissions handled inline in resolvers (compatible with all Strawberry versions)
from django.contrib.auth import get_user_model
from apps.rbac.models import Role, ControlPoint, ControlPointGroup
from apps.lookup.models import LookupValue

User = get_user_model()


# ── Permissions ──

def get_request(info):
    """Extract Django request from Strawberry info context."""
    ctx = info.context
    return ctx["request"] if isinstance(ctx, dict) else ctx.request


def require_auth(info):
    """Raise PermissionError if not authenticated."""
    request = get_request(info)
    if not request.user.is_authenticated:
        raise PermissionError("Authentication required")


def require_superuser(info):
    """Raise PermissionError if not superuser."""
    request = get_request(info)
    if not request.user.is_authenticated or not request.user.is_superuser:
        raise PermissionError("Superuser access required")


# ── Types ──

@strawberry.django.type(User)
class UserType:
    id: auto
    email: auto
    first_name: auto
    last_name: auto
    is_active: auto
    is_staff: auto
    is_superuser: auto

    @strawberry.field
    def roles(self) -> List["RoleType"]:
        return self.roles.all()


@strawberry.django.type(Role)
class RoleType:
    id: auto
    name: auto
    description: auto
    is_active: auto

    @strawberry.field
    def control_points(self) -> List["ControlPointType"]:
        return self.control_points.all()

    @strawberry.field
    def control_point_count(self) -> int:
        return self.control_points.count()


@strawberry.django.type(ControlPointGroup)
class ControlPointGroupType:
    id: auto
    name: auto
    description: auto
    sort_order: auto
    is_active: auto


@strawberry.django.type(ControlPoint)
class ControlPointType:
    id: auto
    code: auto
    label: auto
    description: auto
    is_active: auto

    @strawberry.field
    def group(self) -> ControlPointGroupType:
        return self.group

    @strawberry.field
    def group_name(self) -> str:
        return self.group.name


@strawberry.django.type(LookupValue)
class LookupValueType:
    id: auto
    code: auto
    label: auto
    description: auto
    sort_order: auto
    is_active: auto

    @strawberry.field
    def parent(self) -> Optional["LookupValueType"]:
        return self.parent

    @strawberry.field
    def parent_label(self) -> str:
        return self.parent.label if self.parent else "(Type)"


# ── Pagination ──

@strawberry.type
class PageInfo:
    total_count: int
    page: int
    page_size: int
    total_pages: int


@strawberry.type
class UserConnection:
    items: List[UserType]
    page_info: PageInfo


@strawberry.type
class RoleConnection:
    items: List[RoleType]
    page_info: PageInfo


@strawberry.type
class ControlPointConnection:
    items: List[ControlPointType]
    page_info: PageInfo


@strawberry.type
class ControlPointGroupConnection:
    items: List[ControlPointGroupType]
    page_info: PageInfo


@strawberry.type
class LookupValueConnection:
    items: List[LookupValueType]
    page_info: PageInfo


def paginate(qs, page: int = 1, page_size: int = 25, search: str = "", search_fields: list = None, order_by: str = ""):
    """Apply search, ordering, and pagination to a queryset."""
    from django.db.models import Q
    if search and search_fields:
        q = Q()
        for field in search_fields:
            q |= Q(**{f"{field}__icontains": search})
        qs = qs.filter(q)
    if order_by:
        desc = order_by.startswith("-")
        field = order_by.lstrip("-")
        qs = qs.order_by(f"-{field}" if desc else field)
    total = qs.count()
    start = (page - 1) * page_size
    items = list(qs[start:start + page_size])
    return items, PageInfo(
        total_count=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


# ── Queries ──

@strawberry.type
class Query:
    @strawberry.field
    def me(self, info: Info) -> UserType:
        require_auth(info)
        return get_request(info).user

    @strawberry.field
    def users(
        self, page: int = 1, page_size: int = 25, search: str = "", order_by: str = "email"
    ) -> UserConnection:
        qs = User.all_objects.all()
        items, page_info = paginate(qs, page, page_size, search, ["email", "first_name", "last_name"], order_by)
        return UserConnection(items=items, page_info=page_info)

    @strawberry.field
    def user(self, id: uuid.UUID) -> Optional[UserType]:
        return User.all_objects.filter(pk=id).first()

    @strawberry.field
    def roles(
        self, page: int = 1, page_size: int = 25, search: str = "", order_by: str = "name"
    ) -> RoleConnection:
        qs = Role.objects.all()
        items, page_info = paginate(qs, page, page_size, search, ["name", "description"], order_by)
        return RoleConnection(items=items, page_info=page_info)

    @strawberry.field
    def role(self, id: uuid.UUID) -> Optional[RoleType]:
        return Role.objects.filter(pk=id).first()

    @strawberry.field
    def control_points(
        self, page: int = 1, page_size: int = 25, search: str = "", order_by: str = "label"
    ) -> ControlPointConnection:
        qs = ControlPoint.objects.select_related("group").all()
        items, page_info = paginate(qs, page, page_size, search, ["code", "label", "group__name"], order_by)
        return ControlPointConnection(items=items, page_info=page_info)

    @strawberry.field
    def control_point_groups(
        self, page: int = 1, page_size: int = 25, search: str = "", order_by: str = "sort_order"
    ) -> ControlPointGroupConnection:
        qs = ControlPointGroup.objects.all()
        items, page_info = paginate(qs, page, page_size, search, ["name", "description"], order_by)
        return ControlPointGroupConnection(items=items, page_info=page_info)

    @strawberry.field
    def lookup_values(
        self, page: int = 1, page_size: int = 25, search: str = "", order_by: str = "sort_order",
        parent_is_null: Optional[bool] = None,
    ) -> LookupValueConnection:
        qs = LookupValue.all_objects.select_related("parent").all()
        if parent_is_null is True:
            qs = qs.filter(parent__isnull=True)
        elif parent_is_null is False:
            qs = qs.filter(parent__isnull=False)
        items, page_info = paginate(qs, page, page_size, search, ["code", "label"], order_by)
        return LookupValueConnection(items=items, page_info=page_info)


# ── Input Types ──

@strawberry.input
class UserInput:
    email: str
    first_name: str = ""
    last_name: str = ""
    is_active: bool = True
    is_staff: bool = False
    is_superuser: bool = False
    role_ids: Optional[List[uuid.UUID]] = None


@strawberry.input
class RoleInput:
    name: str
    description: str = ""
    control_point_ids: Optional[List[uuid.UUID]] = None


@strawberry.input
class ControlPointInput:
    group_id: uuid.UUID
    code: str
    label: str
    description: str = ""


@strawberry.input
class ControlPointGroupInput:
    name: str
    description: str = ""
    sort_order: int = 0


@strawberry.input
class LookupValueInput:
    code: str
    label: str
    parent_id: Optional[uuid.UUID] = None
    description: str = ""
    sort_order: int = 0
    is_active: bool = True


# ── Mutations ──

@strawberry.type
class Mutation:
    # Users
    @strawberry.mutation
    def create_user(self, input: UserInput) -> UserType:
        user = User.objects.create_user(
            email=input.email, first_name=input.first_name, last_name=input.last_name,
            is_active=input.is_active, is_staff=input.is_staff, is_superuser=input.is_superuser,
        )
        if input.role_ids:
            user.roles.set(Role.objects.filter(pk__in=input.role_ids))
        return user

    @strawberry.mutation
    def update_user(self, id: uuid.UUID, input: UserInput) -> UserType:
        user = User.all_objects.get(pk=id)
        user.email = input.email
        user.first_name = input.first_name
        user.last_name = input.last_name
        user.is_active = input.is_active
        user.is_staff = input.is_staff
        user.is_superuser = input.is_superuser
        user.save()
        if input.role_ids is not None:
            user.roles.set(Role.objects.filter(pk__in=input.role_ids))
        return user

    @strawberry.mutation
    def delete_user(self, id: uuid.UUID) -> bool:
        user = User.all_objects.get(pk=id)
        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        return True

    # Roles
    @strawberry.mutation
    def create_role(self, input: RoleInput) -> RoleType:
        role = Role.objects.create(name=input.name, description=input.description)
        if input.control_point_ids:
            role.control_points.set(ControlPoint.objects.filter(pk__in=input.control_point_ids))
        return role

    @strawberry.mutation
    def update_role(self, id: uuid.UUID, input: RoleInput) -> RoleType:
        role = Role.objects.get(pk=id)
        role.name = input.name
        role.description = input.description
        role.save()
        if input.control_point_ids is not None:
            role.control_points.set(ControlPoint.objects.filter(pk__in=input.control_point_ids))
        return role

    @strawberry.mutation
    def delete_role(self, id: uuid.UUID) -> bool:
        role = Role.objects.get(pk=id)
        role.is_active = False
        role.save(update_fields=["is_active", "updated_at"])
        return True

    # Control Points
    @strawberry.mutation
    def create_control_point(self, input: ControlPointInput) -> ControlPointType:
        return ControlPoint.objects.create(
            group_id=input.group_id, code=input.code, label=input.label, description=input.description,
        )

    @strawberry.mutation
    def update_control_point(self, id: uuid.UUID, input: ControlPointInput) -> ControlPointType:
        cp = ControlPoint.objects.get(pk=id)
        cp.group_id = input.group_id
        cp.code = input.code
        cp.label = input.label
        cp.description = input.description
        cp.save()
        return cp

    @strawberry.mutation
    def delete_control_point(self, id: uuid.UUID) -> bool:
        cp = ControlPoint.objects.get(pk=id)
        cp.is_active = False
        cp.save(update_fields=["is_active", "updated_at"])
        return True

    # Control Point Groups
    @strawberry.mutation
    def create_control_point_group(self, input: ControlPointGroupInput) -> ControlPointGroupType:
        return ControlPointGroup.objects.create(
            name=input.name, description=input.description, sort_order=input.sort_order,
        )

    @strawberry.mutation
    def update_control_point_group(self, id: uuid.UUID, input: ControlPointGroupInput) -> ControlPointGroupType:
        g = ControlPointGroup.objects.get(pk=id)
        g.name = input.name
        g.description = input.description
        g.sort_order = input.sort_order
        g.save()
        return g

    @strawberry.mutation
    def delete_control_point_group(self, id: uuid.UUID) -> bool:
        g = ControlPointGroup.objects.get(pk=id)
        g.is_active = False
        g.save(update_fields=["is_active", "updated_at"])
        return True

    # Lookup Values
    @strawberry.mutation
    def create_lookup_value(self, input: LookupValueInput) -> LookupValueType:
        return LookupValue.objects.create(
            parent_id=input.parent_id, code=input.code, label=input.label,
            description=input.description, sort_order=input.sort_order, is_active=input.is_active,
        )

    @strawberry.mutation
    def update_lookup_value(self, id: uuid.UUID, input: LookupValueInput) -> LookupValueType:
        lv = LookupValue.all_objects.get(pk=id)
        lv.parent_id = input.parent_id
        lv.code = input.code
        lv.label = input.label
        lv.description = input.description
        lv.sort_order = input.sort_order
        lv.is_active = input.is_active
        lv.save()
        return lv

    @strawberry.mutation
    def delete_lookup_value(self, id: uuid.UUID) -> bool:
        lv = LookupValue.all_objects.get(pk=id)
        lv.is_active = False
        lv.save(update_fields=["is_active", "updated_at"])
        return True


schema = strawberry.Schema(query=Query, mutation=Mutation)
