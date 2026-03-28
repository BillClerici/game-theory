import { useState } from 'react'
import { useQuery } from '@apollo/client'
import { Typography } from '@mui/material'
import { GridColDef } from '@mui/x-data-grid'
import GraphQLDataGrid from '../../components/GraphQLDataGrid'
import GraphQLEntityForm, { FieldDef } from '../../components/GraphQLEntityForm'
import GraphQLDeleteDialog from '../../components/GraphQLDeleteDialog'
import { LOOKUP_VALUES_QUERY, LOOKUP_TYPES_QUERY } from '../../api/queries'
import { CREATE_LOOKUP, UPDATE_LOOKUP, DELETE_LOOKUP } from '../../api/mutations'

const columns: GridColDef[] = [
  { field: 'parentLabel', headerName: 'Type/Parent', flex: 1 },
  { field: 'code', headerName: 'Code', flex: 1 },
  { field: 'label', headerName: 'Label', flex: 1 },
  { field: 'sortOrder', headerName: 'Sort', width: 80, type: 'number' },
  { field: 'isActive', headerName: 'Active', width: 80, type: 'boolean' },
]

export default function Lookups() {
  const [formOpen, setFormOpen] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [deleteName, setDeleteName] = useState('')
  const { data: typesData } = useQuery(LOOKUP_TYPES_QUERY)
  const [refresh, setRefresh] = useState(0)

  const parentOptions = (typesData?.lookupValues?.items || []).map((p: any) => ({
    value: p.id, label: p.label
  }))

  const fields: FieldDef[] = [
    { name: 'parentId', label: 'Parent (Type)', type: 'select', options: parentOptions, helpText: 'Leave blank for a new type', graphqlName: 'parentId' },
    { name: 'code', label: 'Code', required: true },
    { name: 'label', label: 'Label', required: true },
    { name: 'description', label: 'Description' },
    { name: 'sortOrder', label: 'Sort Order', type: 'number', graphqlName: 'sortOrder' },
    { name: 'isActive', label: 'Active', type: 'checkbox', graphqlName: 'isActive' },
  ]

  return (
    <>
      <Typography variant="h5" gutterBottom>Lookup Items</Typography>
      <GraphQLDataGrid key={refresh} title="Lookups" query={LOOKUP_VALUES_QUERY} dataKey="lookupValues" columns={columns}
        onAdd={() => { setEditId(null); setFormOpen(true) }}
        onEdit={(id) => { setEditId(id); setFormOpen(true) }}
        onDelete={(id) => { setDeleteId(id); setDeleteName(id); setDeleteOpen(true) }}
      />
      <GraphQLEntityForm open={formOpen} onClose={() => setFormOpen(false)}
        onSaved={() => setRefresh(r => r + 1)} title="Lookup Item" fields={fields}
        createMutation={CREATE_LOOKUP} updateMutation={UPDATE_LOOKUP}
        editId={editId} />
      <GraphQLDeleteDialog open={deleteOpen} onClose={() => setDeleteOpen(false)}
        onDeleted={() => setRefresh(r => r + 1)}
        mutation={DELETE_LOOKUP} deleteId={deleteId} itemName={deleteName} />
    </>
  )
}
