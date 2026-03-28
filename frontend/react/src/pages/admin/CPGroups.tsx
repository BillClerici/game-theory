import { useState } from 'react'
import { Typography } from '@mui/material'
import { GridColDef } from '@mui/x-data-grid'
import GraphQLDataGrid from '../../components/GraphQLDataGrid'
import GraphQLEntityForm, { FieldDef } from '../../components/GraphQLEntityForm'
import GraphQLDeleteDialog from '../../components/GraphQLDeleteDialog'
import { CP_GROUPS_QUERY } from '../../api/queries'
import { CREATE_CP_GROUP, UPDATE_CP_GROUP, DELETE_CP_GROUP } from '../../api/mutations'

const columns: GridColDef[] = [
  { field: 'name', headerName: 'Name', flex: 1 },
  { field: 'description', headerName: 'Description', flex: 2 },
  { field: 'sortOrder', headerName: 'Sort Order', width: 110, type: 'number' },
]

const fields: FieldDef[] = [
  { name: 'name', label: 'Group Name', required: true },
  { name: 'description', label: 'Description' },
  { name: 'sortOrder', label: 'Sort Order', type: 'number', graphqlName: 'sortOrder' },
]

export default function CPGroups() {
  const [formOpen, setFormOpen] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [deleteName, setDeleteName] = useState('')
  const [refresh, setRefresh] = useState(0)

  return (
    <>
      <Typography variant="h5" gutterBottom>Control Point Groups</Typography>
      <GraphQLDataGrid key={refresh} title="CP Groups" query={CP_GROUPS_QUERY} dataKey="controlPointGroups" columns={columns}
        onAdd={() => { setEditId(null); setFormOpen(true) }}
        onEdit={(id) => { setEditId(id); setFormOpen(true) }}
        onDelete={(id) => { setDeleteId(id); setDeleteName(id); setDeleteOpen(true) }}
      />
      <GraphQLEntityForm open={formOpen} onClose={() => setFormOpen(false)}
        onSaved={() => setRefresh(r => r + 1)} title="CP Group" fields={fields}
        createMutation={CREATE_CP_GROUP} updateMutation={UPDATE_CP_GROUP}
        editId={editId} />
      <GraphQLDeleteDialog open={deleteOpen} onClose={() => setDeleteOpen(false)}
        onDeleted={() => setRefresh(r => r + 1)}
        mutation={DELETE_CP_GROUP} deleteId={deleteId} itemName={deleteName} />
    </>
  )
}
