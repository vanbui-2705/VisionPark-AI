import { useCallback, useEffect, useState } from 'react'
import { lanesApi, type LanePayload } from '../../api/lanesApi.ts'
import type { Lane } from '../../api/types.ts'
import { ApiError } from '../../api/errors.ts'

export function useLanes() {
  const [lanes, setLanes] = useState<Lane[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await lanesApi.getLanes()
      setLanes(Array.isArray(data) ? data : [])
    } catch (e) {
      setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Failed to load lanes')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const createLane = useCallback(
    async (payload: LanePayload) => {
      const lane = await lanesApi.createLane(payload)
      setLanes((prev) => [...prev, lane])
      return lane
    },
    [],
  )

  const updateLane = useCallback(async (id: string, payload: Partial<LanePayload>) => {
    const lane = await lanesApi.updateLane(id, payload)
    setLanes((prev) => prev.map((l) => (l.id === id ? lane : l)))
    return lane
  }, [])

  const inactive = useCallback(async (id: string) => {
    const lane = await lanesApi.setLaneInactive(id)
    setLanes((prev) => prev.map((l) => (l.id === id ? lane : l)))
    return lane
  }, [])

  return { lanes, loading, error, refresh, createLane, updateLane, inactive }
}
