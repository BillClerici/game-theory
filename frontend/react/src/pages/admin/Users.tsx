import { useState, useEffect } from 'react'
import { useQuery } from '@apollo/client'
import { Typography } from '@mui/material'
import { GridColDef } from '@mui/x-data-grid'
import GraphQLDataGrid from '../../components/GraphQLDataGrid'
import GraphQLEntityForm, { FieldDef } from '../../components/GraphQLEntityForm'
import GraphQLDeleteDialog from '../../components/GraphQLDeleteDialog'
import { USERS_QUERY, USER_QUERY, ROLES_QUERY } from '../../api/queries'
import { CREATE_USER, UPDATE_USER, DELETE_USER } from '../../api/mutations'

const columns: GridColDef[] = [
  { field: 'email', headerName: 'Email', flex: 1, minWidth: 200 },
  { field: 'firstName', headerName: 'First Name', flex: 1 },
  { field: 'lastName', headerName: 'Last Name', flex: 1 },
  { field: 'isStaff', headerName: 'Staff', width: 80, type: 'boolean' },
  { field: 'isSuperuser', headerName: 'Super', width: 80, type: 'boolean' },
  { field: 'isActive', headerName: 'Active', width: 80, type: 'boolean' },
]

export default function Users() {
  const [formOpen, setFormOpen] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [deleteName, setDeleteName] = useState('')
  const { data: rolesData } = useQuery(ROLES_QUERY, { variables: { page: 1, pageSize: 100 } })
  const [refresh, setRefresh] = useState(0)

  const roleOptions = (rolesData?.roles?.items || []).map((r: any) => ({ value: r.id, label: r.name }))

  const fields: FieldDef[] = [
    { name: 'email', label: 'Email', type: 'email', required: true },
    { name: 'firstName', label: 'First Name', graphqlName: 'firstName' },
    { name: 'lastName', label: 'Last Name', graphqlName: 'lastName' },
    { name: 'isActive', label: 'Active', type: 'checkbox', graphqlName: 'isActive' },
    { name: 'isStaff', label: 'Staff', type: 'checkbox', graphqlName: 'isStaff' },
    { name: 'isSuperuser', label: 'Superuser', type: 'checkbox', graphqlName: 'isSuperuser' },
    { name: 'roleIds', label: 'Roles', type: 'multiselect', options: roleOptions, graphqlName: 'roleIds' },
  ]

  return (
    <>
      <Typography variant="h5" gutterBottom>Users</Typography>
      <GraphQLDataGrid key={refresh} title="Users" query={USERS_QUERY} dataKey="users" columns={columns}
        onAdd={() => { setEditId(null); setFormOpen(true) }}
        onEdit={(id) => { setEditId(id); setFormOpen(true) }}
        onDelete={(id) => { setDeleteId(id); setDeleteName(id); setDeleteOpen(true) }}
      />
      <GraphQLEntityForm open={formOpen} onClose={() => setFormOpen(false)}
        onSaved={() => setRefresh(r => r + 1)} title="User" fields={fields}
        createMutation={CREATE_USER} updateMutation={UPDATE_USER}
        fetchQuery={USER_QUERY} fetchDataKey="user" editId={editId} />
      <GraphQLDeleteDialog open={deleteOpen} onClose={() => setDeleteOpen(false)}
        onDeleted={() => setRefresh(r => r + 1)}
        mutation={DELETE_USER} deleteId={deleteId} itemName={deleteName} />
    </>
  )
}
