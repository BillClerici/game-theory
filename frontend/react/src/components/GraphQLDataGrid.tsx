import { useState } from 'react'
import { useQuery, DocumentNode } from '@apollo/client'
import { DataGrid as MuiDataGrid, GridColDef, GridPaginationModel, GridSortModel } from '@mui/x-data-grid'
import { Box, TextField, InputAdornment, Button, IconButton } from '@mui/material'
import { Search, Add, Edit, Delete } from '@mui/icons-material'

interface Props {
  title: string
  query: DocumentNode
  dataKey: string
  columns: GridColDef[]
  onAdd?: () => void
  onEdit?: (id: string) => void
  onDelete?: (id: string) => void
  extraVariables?: Record<string, any>
}

export default function GraphQLDataGrid({
  title, query, dataKey, columns, onAdd, onEdit, onDelete, extraVariables = {}
}: Props) {
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({ page: 0, pageSize: 25 })
  const [search, setSearch] = useState('')
  const [sortModel, setSortModel] = useState<GridSortModel>([])

  const orderBy = sortModel.length > 0
    ? `${sortModel[0].sort === 'desc' ? '-' : ''}${sortModel[0].field}`
    : ''

  const { data, loading } = useQuery(query, {
    variables: {
      page: paginationModel.page + 1,
      pageSize: paginationModel.pageSize,
      search: search || undefined,
      orderBy: orderBy || undefined,
      ...extraVariables,
    },
  })

  const result = data?.[dataKey]
  const rows = result?.items || []
  const totalCount = result?.pageInfo?.totalCount || 0

  const actionColumn: GridColDef = {
    field: 'actions',
    headerName: 'Actions',
    width: 120,
    sortable: false,
    filterable: false,
    renderCell: (params) => (
      <Box>
        {onEdit && (
          <IconButton size="small" onClick={() => onEdit(params.row.id)} title="Edit">
            <Edit fontSize="small" />
          </IconButton>
        )}
        {onDelete && (
          <IconButton size="small" color="error" onClick={() => onDelete(params.row.id)} title="Delete">
            <Delete fontSize="small" />
          </IconButton>
        )}
      </Box>
    ),
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <TextField
          size="small"
          placeholder={`Search ${title.toLowerCase()}...`}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          InputProps={{
            startAdornment: <InputAdornment position="start"><Search /></InputAdornment>,
          }}
          sx={{ minWidth: 300 }}
        />
        {onAdd && (
          <Button variant="contained" startIcon={<Add />} onClick={onAdd}>Add New</Button>
        )}
      </Box>
      <MuiDataGrid
        rows={rows}
        columns={[...columns, actionColumn]}
        loading={loading}
        rowCount={totalCount}
        pageSizeOptions={[10, 25, 50, 100]}
        paginationModel={paginationModel}
        onPaginationModelChange={setPaginationModel}
        paginationMode="server"
        sortingMode="server"
        sortModel={sortModel}
        onSortModelChange={setSortModel}
        disableRowSelectionOnClick
        autoHeight
        sx={{ bgcolor: '#fff' }}
      />
    </Box>
  )
}
