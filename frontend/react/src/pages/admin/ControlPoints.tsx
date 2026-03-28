import { useState } from 'react'
import { useQuery } from '@apollo/client'
import { Typography } from '@mui/material'
import { GridColDef } from '@mui/x-data-grid'
import GraphQLDataGrid from '../../components/GraphQLDataGrid'
import GraphQLEntityForm, { FieldDef } from '../../components/GraphQLEntityForm'
import GraphQLDeleteDialog from '../../components/GraphQLDeleteDialog'
import { CONTROL_POINTS_QUERY, CP_GROUPS_QUERY } from '../../api/queries'
import { CREATE_CONTROL_POINT, UPDATE_CONTROL_POINT, DELETE_CONTROL_POINT } from '../../api/mutations'

const columns: GridColDef[] = [
  { field: 'groupName', headerName: 'Group', flex: 1 },
  { field: 'code', headerName: 'Code', flex: 1 },
  { field: 'label', headerName: 'Label', flex: 1 },
]

export default function ControlPoints() {
  const [formOpen, setFormOpen] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [deleteName, setDeleteName] = useState('')
  const { data: groupsData } = useQuery(CP_GROUPS_QUERY, { variables: { page: 1, pageSize: 100 } })
  const [refresh, setRefresh] = useState(0)

  const groupOptions = (groupsData?.controlPointGroups?.items || []).map((g: any) => ({
    value: g.id, label: g.name
  }))

  const fields: FieldDef[] = [
    { name: 'groupId', label: 'Group', type: 'select', options: groupOptions, required: true, graphqlName: 'groupId' },
    { name: 'code', label: 'Code', required: true },
    { name: 'label', label: 'Label', required: true },
    { name: 'description', label: 'Description' },
  ]

  return (
    <>
      <Typography variant="h5" gutterBottom>Control Points</Typography>
      <GraphQLDataGrid key={refresh} title="Control Points" query={CONTROL_POINTS_QUERY} dataKey="controlPoints" columns={columns}
        onAdd={() => { setEditId(null); setFormOpen(true) }}
        onEdit={(id) => { setEditId(id); setFormOpen(true) }}
        onDelete={(id) => { setDeleteId(id); setDeleteName(id); setDeleteOpen(true) }}
      />
      <GraphQLEntityForm open={formOpen} onClose={() => setFormOpen(false)}
        onSaved={() => setRefresh(r => r + 1)} title="Control Point" fields={fields}
        createMutation={CREATE_CONTROL_POINT} updateMutation={UPDATE_CONTROL_POINT}
        editId={editId} />
      <GraphQLDeleteDialog open={deleteOpen} onClose={() => setDeleteOpen(false)}
        onDeleted={() => setRefresh(r => r + 1)}
        mutation={DELETE_CONTROL_POINT} deleteId={deleteId} itemName={deleteName} />
    </>
  )
}
