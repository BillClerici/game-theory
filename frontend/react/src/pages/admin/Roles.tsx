import { useState } from 'react'
import { useQuery } from '@apollo/client'
import { Typography } from '@mui/material'
import { GridColDef } from '@mui/x-data-grid'
import GraphQLDataGrid from '../../components/GraphQLDataGrid'
import GraphQLEntityForm, { FieldDef } from '../../components/GraphQLEntityForm'
import GraphQLDeleteDialog from '../../components/GraphQLDeleteDialog'
import { ROLES_QUERY, ROLE_QUERY, CONTROL_POINTS_QUERY } from '../../api/queries'
import { CREATE_ROLE, UPDATE_ROLE, DELETE_ROLE } from '../../api/mutations'

const columns: GridColDef[] = [
  { field: 'name', headerName: 'Name', flex: 1 },
  { field: 'description', headerName: 'Description', flex: 2 },
  { field: 'controlPointCount', headerName: 'Control Points', width: 130, type: 'number' },
]

export default function Roles() {
  const [formOpen, setFormOpen] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [deleteName, setDeleteName] = useState('')
  const { data: cpData } = useQuery(CONTROL_POINTS_QUERY, { variables: { page: 1, pageSize: 200 } })
  const [refresh, setRefresh] = useState(0)

  const cpOptions = (cpData?.controlPoints?.items || []).map((cp: any) => ({
    value: cp.id, label: `${cp.groupName} > ${cp.label}`
  }))

  const fields: FieldDef[] = [
    { name: 'name', label: 'Role Name', required: true },
    { name: 'description', label: 'Description' },
    { name: 'controlPointIds', label: 'Control Points', type: 'multiselect', options: cpOptions, graphqlName: 'controlPointIds' },
  ]

  return (
    <>
      <Typography variant="h5" gutterBottom>Roles</Typography>
      <GraphQLDataGrid key={refresh} title="Roles" query={ROLES_QUERY} dataKey="roles" columns={columns}
        onAdd={() => { setEditId(null); setFormOpen(true) }}
        onEdit={(id) => { setEditId(id); setFormOpen(true) }}
        onDelete={(id) => { setDeleteId(id); setDeleteName(id); setDeleteOpen(true) }}
      />
      <GraphQLEntityForm open={formOpen} onClose={() => setFormOpen(false)}
        onSaved={() => setRefresh(r => r + 1)} title="Role" fields={fields}
        createMutation={CREATE_ROLE} updateMutation={UPDATE_ROLE}
        fetchQuery={ROLE_QUERY} fetchDataKey="role" editId={editId} />
      <GraphQLDeleteDialog open={deleteOpen} onClose={() => setDeleteOpen(false)}
        onDeleted={() => setRefresh(r => r + 1)}
        mutation={DELETE_ROLE} deleteId={deleteId} itemName={deleteName} />
    </>
  )
}
