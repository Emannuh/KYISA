import { useState, useEffect, useCallback } from 'react'
import toast from 'react-hot-toast'

/**
 * Generic data fetching hook with loading, error, and refetch.
 */
export function useFetch(apiFn, deps = [], options = {}) {
  const { immediate = true, onSuccess, onError } = options
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(immediate)
  const [error, setError] = useState(null)

  const execute = useCallback(async (...args) => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiFn(...args)
      setData(res.data)
      onSuccess?.(res.data)
      return res.data
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Something went wrong'
      setError(msg)
      onError?.(msg)
      throw err
    } finally {
      setLoading(false)
    }
  }, deps) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (immediate) execute()
  }, [execute, immediate])

  return { data, loading, error, refetch: execute, setData }
}

/**
 * Debounced value hook for search inputs.
 */
export function useDebounce(value, delay = 400) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return debounced
}

/**
 * Mutation hook for POST/PATCH/DELETE with toast feedback.
 */
export function useMutation(apiFn, options = {}) {
  const { successMessage, onSuccess, onError } = options
  const [loading, setLoading] = useState(false)

  const mutate = useCallback(async (...args) => {
    setLoading(true)
    try {
      const res = await apiFn(...args)
      if (successMessage) toast.success(successMessage)
      onSuccess?.(res.data)
      return res.data
    } catch (err) {
      const msg = err.response?.data?.detail
        || Object.values(err.response?.data || {}).flat().join(', ')
        || 'Operation failed'
      toast.error(msg)
      onError?.(err)
      throw err
    } finally {
      setLoading(false)
    }
  }, [apiFn]) // eslint-disable-line react-hooks/exhaustive-deps

  return { mutate, loading }
}
