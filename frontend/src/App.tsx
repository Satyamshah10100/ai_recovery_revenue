import { useEffect, useState } from 'react'
import { supabase } from './supabaseClient'

export default function App() {
  const [events, setEvents] = useState<any[]>([])

  useEffect(() => {
    fetchData()
    
    // Optional: Set up an interval to poll for new data every 5 seconds
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchData = async () => {
    // Fetch failed events and join the corresponding recovery attempt lock
    const { data, error } = await supabase
      .from('failed_events')
      .select(`
        *,
        recovery_attempts ( ai_diagnosis_class, ai_confidence, action_taken )
      `)
      .order('created_at', { ascending: false })

    if (!error && data) setEvents(data)
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">AI Recovery Console</h1>
        <p className="text-gray-500 mb-8">Real-time payment failure diagnostics and deterministic recovery.</p>
        
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-800">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Event ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Raw Error</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">AI Diagnosis</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">System Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {events.map((evt) => {
                const aiData = evt.recovery_attempts?.[0] || {}
                
                return (
                  <tr key={evt.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {evt.webhook_event_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-red-600 font-semibold">
                      {evt.error_code}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {aiData.ai_diagnosis_class ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          {aiData.ai_diagnosis_class} ({(aiData.ai_confidence * 100).toFixed(0)}%)
                        </span>
                      ) : 'Processing...'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {aiData.action_taken ? (
                        <span className="font-mono bg-gray-100 px-2 py-1 rounded">
                          {aiData.action_taken}
                        </span>
                      ) : '-'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}