import { useState, useEffect } from 'react'
import { useMutation, useQuery, DocumentNode, gql } from '@apollo/client'
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, FormControlLabel, Checkbox, MenuItem, Select,
  InputLabel, FormControl, FormHelperText, Box,
} from '@mui/material'

export interface FieldDef {
  name: string
  label: string
  type?: 'text' | 'email' | 'checkbox' | 'select' | 'multiselect' | 'number'
  required?: boolean
  helpText?: string
  options?: { value: string; label: string }[]
  graphqlName?: string  // maps form field name to GraphQL input field name
}

interface Props {
  open: boolean
  onClose: () => void
  onSaved: () => void
  title: string
  fields: FieldDef[]
  createMutation: DocumentNode
  updateMutation: DocumentNode
  fetchQuery?: DocumentNode
  fetchDataKey?: string
  editId?: string | null
}

export default function GraphQLEntityForm({
  open, onClose, onSaved, title, fields, createMutation, updateMutation,
  fetchQuery, fetchDataKey, editId
}: Props) {
  const [values, setValues] = useState<Record<string, any>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})

  // Use a no-op query when fetchQuery isn't provided (Apollo requires a valid document)
  const NOOP_QUERY = gql`query Noop { __typename }`
  const { data: fetchData } = useQuery(fetchQuery || NOOP_QUERY, {
    variables: fetchQuery ? { id: editId } : {},
    skip: !editId || !fetchQuery,
  })

  const [create, { loading: creating }] = useMutation(createMutation)
  const [update, { loading: updating }] = useMutation(updateMutation)

  useEffect(() => {
    if (open && editId && fetchData && fetchDataKey) {
      const item = fetchData[fetchDataKey]
      if (item) {
        const v: Record<string, any> = {}
        fields.forEach(f => {
          const gqlName = f.graphqlName || f.name
          if (f.type === 'multiselect' && Array.isArray(item[gqlName])) {
            v[f.name] = item[gqlName].map((x: any) => x.id || x)
          } else {
            v[f.name] = item[gqlName] ?? (f.type === 'checkbox' ? false : '')
          }
        })
        setValues(v)
      }
    } else if (open && !editId) {
      const defaults: Record<string, any> = {}
      fields.forEach(f => {
        if (f.type === 'checkbox') defaults[f.name] = false
        else if (f.type === 'multiselect') defaults[f.name] = []
        else if (f.type === 'number') defaults[f.name] = 0
        else defaults[f.name] = ''
      })
      setValues(defaults)
    }
    setErrors({})
  }, [open, editId, fetchData])

  const handleSubmit = async () => {
    setErrors({})
    // Build input object using graphqlName mappings
    const input: Record<string, any> = {}
    fields.forEach(f => {
      const gqlName = f.graphqlName || f.name
      input[gqlName] = values[f.name]
    })
    try {
      if (editId) {
        await update({ variables: { id: editId, input } })
      } else {
        await create({ variables: { input } })
      }
      onSaved()
      onClose()
    } catch (err: any) {
      const msg = err?.graphQLErrors?.[0]?.message || err?.message || 'Save failed'
      setErrors({ _form: msg })
    }
  }

  const setValue = (name: string, value: any) => setValues(prev => ({ ...prev, [name]: value }))
  const loading = creating || updating

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{editId ? 'Edit' : 'Create'} {title}</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
          {errors._form && (
            <Box sx={{ color: 'error.main', fontSize: '0.875rem' }}>{errors._form}</Box>
          )}
          {fields.map(field => {
            if (field.type === 'checkbox') {
              return (
                <FormControlLabel key={field.name}
                  control={<Checkbox checked={!!values[field.name]} onChange={e => setValue(field.name, e.target.checked)} />}
                  label={field.label}
                />
              )
            }
            if (field.type === 'select') {
              return (
                <FormControl key={field.name} fullWidth>
                  <InputLabel>{field.label}</InputLabel>
                  <Select value={values[field.name] || ''} label={field.label}
                    onChange={e => setValue(field.name, e.target.value)}>
                    <MenuItem value=""><em>None</em></MenuItem>
                    {field.options?.map(o => <MenuItem key={o.value} value={o.value}>{o.label}</MenuItem>)}
                  </Select>
                  {field.helpText && <FormHelperText>{field.helpText}</FormHelperText>}
                </FormControl>
              )
            }
            if (field.type === 'multiselect') {
              return (
                <FormControl key={field.name} fullWidth>
                  <InputLabel>{field.label}</InputLabel>
                  <Select multiple value={values[field.name] || []} label={field.label}
                    onChange={e => setValue(field.name, e.target.value)}>
                    {field.options?.map(o => <MenuItem key={o.value} value={o.value}>{o.label}</MenuItem>)}
                  </Select>
                  {field.helpText && <FormHelperText>{field.helpText}</FormHelperText>}
                </FormControl>
              )
            }
            return (
              <TextField key={field.name} fullWidth label={field.label}
                type={field.type || 'text'}
                required={field.required}
                value={values[field.name] ?? ''}
                onChange={e => setValue(field.name, field.type === 'number' ? Number(e.target.value) : e.target.value)}
                helperText={field.helpText}
              />
            )
          })}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit} disabled={loading}>
          {loading ? 'Saving...' : 'Save'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
