import { gql } from '@apollo/client'

export const ME_QUERY = gql`
  query Me {
    me {
      id
      email
      firstName
      lastName
      isSuperuser
    }
  }
`

export const USERS_QUERY = gql`
  query Users($page: Int!, $pageSize: Int!, $search: String, $orderBy: String) {
    users(page: $page, pageSize: $pageSize, search: $search, orderBy: $orderBy) {
      items {
        id
        email
        firstName
        lastName
        isStaff
        isSuperuser
        isActive
        roles { id name }
      }
      pageInfo { totalCount page pageSize totalPages }
    }
  }
`

export const USER_QUERY = gql`
  query User($id: UUID!) {
    user(id: $id) {
      id
      email
      firstName
      lastName
      isActive
      isStaff
      isSuperuser
      roles { id name }
    }
  }
`

export const ROLES_QUERY = gql`
  query Roles($page: Int!, $pageSize: Int!, $search: String, $orderBy: String) {
    roles(page: $page, pageSize: $pageSize, search: $search, orderBy: $orderBy) {
      items {
        id
        name
        description
        controlPointCount
        isActive
      }
      pageInfo { totalCount page pageSize totalPages }
    }
  }
`

export const ROLE_QUERY = gql`
  query Role($id: UUID!) {
    role(id: $id) {
      id
      name
      description
      controlPoints { id label }
    }
  }
`

export const CONTROL_POINTS_QUERY = gql`
  query ControlPoints($page: Int!, $pageSize: Int!, $search: String, $orderBy: String) {
    controlPoints(page: $page, pageSize: $pageSize, search: $search, orderBy: $orderBy) {
      items {
        id
        groupName
        code
        label
        description
        isActive
      }
      pageInfo { totalCount page pageSize totalPages }
    }
  }
`

export const CP_GROUPS_QUERY = gql`
  query ControlPointGroups($page: Int!, $pageSize: Int!, $search: String, $orderBy: String) {
    controlPointGroups(page: $page, pageSize: $pageSize, search: $search, orderBy: $orderBy) {
      items {
        id
        name
        description
        sortOrder
        isActive
      }
      pageInfo { totalCount page pageSize totalPages }
    }
  }
`

export const LOOKUP_VALUES_QUERY = gql`
  query LookupValues($page: Int!, $pageSize: Int!, $search: String, $orderBy: String, $parentIsNull: Boolean) {
    lookupValues(page: $page, pageSize: $pageSize, search: $search, orderBy: $orderBy, parentIsNull: $parentIsNull) {
      items {
        id
        parentLabel
        code
        label
        description
        sortOrder
        isActive
      }
      pageInfo { totalCount page pageSize totalPages }
    }
  }
`

export const LOOKUP_TYPES_QUERY = gql`
  query LookupTypes {
    lookupValues(page: 1, pageSize: 100, parentIsNull: true) {
      items { id label }
    }
  }
`
