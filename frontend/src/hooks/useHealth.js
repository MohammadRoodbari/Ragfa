import { useState, useCallback } from 'react'
import { fetchHealth } from '../lib/api'

/**
 * useHealth — fetches /health on demand.
 * Returns { status, elasticsearch, redis, loading, check }
 */
export function useHealth() {
  const [state, setState] = useState({
    status: 'unknown', // 'ok' | 'degraded' | 'unknown' | 'offline'
    elasticsearch: null,
    redis: null,
    loading: false,
  })

  const check = useCallback(async () => {
    setState(s => ({ ...s, loading: true }))
    try {
      const data = await fetchHealth()
      setState({
        status: data.status ?? 'unknown',
        elasticsearch: data.elasticsearch ?? false,
        redis: data.redis ?? false,
        loading: false,
      })
    } catch {
      setState({ status: 'offline', elasticsearch: false, redis: false, loading: false })
    }
  }, [])

  return { ...state, check }
}
