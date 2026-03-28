import { gql } from '@apollo/client'

export const CREATE_USER = gql`
  mutation CreateUser($input: UserInput!) {
    createUser(input: $input) { id email }
  }
`
export const UPDATE_USER = gql`
  mutation UpdateUser($id: UUID!, $input: UserInput!) {
    updateUser(id: $id, input: $input) { id email }
  }
`
export const DELETE_USER = gql`
  mutation DeleteUser($id: UUID!) {
    deleteUser(id: $id)
  }
`

export const CREATE_ROLE = gql`
  mutation CreateRole($input: RoleInput!) {
    createRole(input: $input) { id name }
  }
`
export const UPDATE_ROLE = gql`
  mutation UpdateRole($id: UUID!, $input: RoleInput!) {
    updateRole(id: $id, input: $input) { id name }
  }
`
export const DELETE_ROLE = gql`
  mutation DeleteRole($id: UUID!) {
    deleteRole(id: $id)
  }
`

export const CREATE_CONTROL_POINT = gql`
  mutation CreateControlPoint($input: ControlPointInput!) {
    createControlPoint(input: $input) { id code }
  }
`
export const UPDATE_CONTROL_POINT = gql`
  mutation UpdateControlPoint($id: UUID!, $input: ControlPointInput!) {
    updateControlPoint(id: $id, input: $input) { id code }
  }
`
export const DELETE_CONTROL_POINT = gql`
  mutation DeleteControlPoint($id: UUID!) {
    deleteControlPoint(id: $id)
  }
`

export const CREATE_CP_GROUP = gql`
  mutation CreateControlPointGroup($input: ControlPointGroupInput!) {
    createControlPointGroup(input: $input) { id name }
  }
`
export const UPDATE_CP_GROUP = gql`
  mutation UpdateControlPointGroup($id: UUID!, $input: ControlPointGroupInput!) {
    updateControlPointGroup(id: $id, input: $input) { id name }
  }
`
export const DELETE_CP_GROUP = gql`
  mutation DeleteControlPointGroup($id: UUID!) {
    deleteControlPointGroup(id: $id)
  }
`

export const CREATE_LOOKUP = gql`
  mutation CreateLookupValue($input: LookupValueInput!) {
    createLookupValue(input: $input) { id code }
  }
`
export const UPDATE_LOOKUP = gql`
  mutation UpdateLookupValue($id: UUID!, $input: LookupValueInput!) {
    updateLookupValue(id: $id, input: $input) { id code }
  }
`
export const DELETE_LOOKUP = gql`
  mutation DeleteLookupValue($id: UUID!) {
    deleteLookupValue(id: $id)
  }
`
