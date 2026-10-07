import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { ParkingHistoryPage } from '../../src/modules/parking/ParkingHistoryPage'
const txs = [
 {id:'pt-1',license_plate:'29A12345',normalized_plate:'29A12345',status:'PARKED',lane_id:'lane-1',lane_name:'IN',check_in_time:'2026-10-07T00:00:00Z',source:'AI_ACCEPTED'},
 {id:'pt-2',license_plate:'30F88888',normalized_plate:'30F88888',status:'PARKED',lane_id:'lane-1',lane_name:'IN',check_in_time:'2026-10-07T00:00:00Z',source:'MANUAL_ENTRY'},
]
const j = (body: unknown,status=200) => new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json'}})
function start(handler: (url: URL) => Response) {
 vi.spyOn(globalThis,'fetch').mockImplementation(async u => { const url = new URL(String(u)); return url.pathname.includes('/parking/transactions') ? handler(url) : url.pathname.includes('/lanes') ? j([{id:'lane-1',name:'IN',direction:'IN',is_active:true}]) : j([]) })
 render(<MemoryRouter><ParkingHistoryPage /></MemoryRouter>)
}
describe('Parking server history',()=>{
 beforeEach(()=>{localStorage.clear();vi.restoreAllMocks()})
 it('renders database items and server totals',async()=>{
  start(()=>j({items:txs,total:205}))
  expect(await screen.findByText('29A12345')).toBeInTheDocument()
  expect(screen.getByText(/205/)).toBeInTheDocument()
 })
 it('sends search to server and displays matching rows',async()=>{
  const queries:string[]=[]
  start(url=>{const q=url.searchParams.get('q')??'';queries.push(q);const items=txs.filter(t=>t.license_plate.includes(q));return j({items,total:items.length})})
  await screen.findByText('29A12345')
  await userEvent.type(screen.getAllByRole('textbox')[0],'30F')
  await waitFor(()=>expect(screen.queryByText('29A12345')).not.toBeInTheDocument())
  expect(screen.getByText('30F88888')).toBeInTheDocument()
  expect(queries).toContain('30F')
 })
 it('keeps filters visible for an empty result',async()=>{
  start(()=>j({items:[],total:0}))
  await waitFor(()=>expect(screen.getAllByRole('textbox').length).toBeGreaterThan(0))
  expect(screen.queryByText('29A12345')).not.toBeInTheDocument()
 })
 it('shows API error without replacing data with fixtures',async()=>{
  start(()=>j({message:'server failed',code:'FAILED'},500))
  expect(await screen.findByText('server failed')).toBeInTheDocument()
  expect(screen.queryByText('29A12345')).not.toBeInTheDocument()
 })

 it('sends lane filter to server',async()=>{
  const queries:string[]=[]
  start(url=>{queries.push(url.searchParams.get('lane_id')??'');return j({items:txs,total:txs.length})})
  await screen.findByText('29A12345')
  await userEvent.selectOptions(screen.getAllByRole('combobox')[0],'lane-1')
  await waitFor(()=>expect(queries).toContain('lane-1'))
 })
 it('sends status filter to server',async()=>{
  const queries:string[]=[]
  start(url=>{queries.push(url.searchParams.get('status')??'');return j({items:txs,total:txs.length})})
  await screen.findByText('29A12345')
  await userEvent.selectOptions(screen.getAllByRole('combobox')[1],'COMPLETED')
  await waitFor(()=>expect(queries).toContain('COMPLETED'))
 })
 it('sends date range to server',async()=>{
  const queries:string[]=[]
  start(url=>{queries.push(url.searchParams.get('from')??'');return j({items:txs,total:txs.length})})
  await screen.findByText('29A12345')
  const {fireEvent}=await import('@testing-library/react')
  fireEvent.change(document.querySelector('input[type="date"]')!,{target:{value:'2026-10-04'}})
  await waitFor(()=>expect(queries.some(value=>Boolean(value)&&new Date(value).getTime()===new Date('2026-10-04T00:00:00').getTime())).toBe(true))
 })
})
