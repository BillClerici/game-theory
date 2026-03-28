import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Typography } from '@mui/material'
import { useMutation, DocumentNode } from '@apollo/client'

interface Props {
  open: boolean
  onClose: () => void
  onDeleted: () => void
  mutation: DocumentNode
  deleteId: string | null
  itemName: string
}

export default function GraphQLDeleteDialog({ open, onClose, onDeleted, mutation, deleteId, itemName }: Props) {
  const [deleteFn, { loading }] = useMutation(mutation)

  const handleDelete = async () => {
    if (!deleteId) return
    try {
      await deleteFn({ variables: { id: deleteId } })
      onDeleted()
      onClose()
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>Confirm Delete</DialogTitle>
      <DialogContent>
        <Typography>Are you sure you want to delete <strong>{itemName}</strong>?</Typography>
        <Typography variant="body2" color="text.secondary" mt={1}>
          This will soft-delete the record (set is_active = false).
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" color="error" onClick={handleDelete} disabled={loading}>
          {loading ? 'Deleting...' : 'Delete'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
