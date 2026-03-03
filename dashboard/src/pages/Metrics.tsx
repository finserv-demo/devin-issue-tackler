import { useMetrics } from '../api/hooks'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

const PIE_COLORS = ['#6b7280', '#1d76db', '#0e8a16', '#5319e7', '#f59e0b', '#15803d', '#dc2626']

function Metrics() {
  const { data: metrics, isLoading, error } = useMetrics()

  if (isLoading) {
    return <div style={{ padding: '2rem', textAlign: 'center', color: '#6b7280' }}>Loading metrics...</div>
  }

  if (error || !metrics) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#dc2626' }}>
        {error ? `Failed to load metrics: ${error.message}` : 'No metrics available'}
      </div>
    )
  }

  return (
    <div>
      <h1 style={{ fontSize: '22px', color: '#111827', marginBottom: '24px' }}>Metrics</h1>

      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '32px' }}>
        <MetricCard label="Total Processed" value={String(metrics.total_processed)} color="#374151" />
        <MetricCard label="Resolved" value={String(metrics.total_done)} color="#15803d" />
        <MetricCard label="Escalated" value={String(metrics.total_escalated)} color="#dc2626" />
        <MetricCard label="Success Rate" value={`${metrics.success_rate.toFixed(0)}%`} color="#2563eb" />
      </div>

      {/* Charts grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* Throughput chart */}
        <ChartCard title="Issues Resolved vs Opened (Weekly)">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={metrics.throughput}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis dataKey="period" tick={{ fontSize: 11, fill: '#6b7280' }} />
              <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="resolved" stroke="#15803d" strokeWidth={2} name="Resolved" />
              <Line type="monotone" dataKey="opened" stroke="#6b7280" strokeWidth={2} strokeDasharray="5 5" name="Opened" />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Pipeline distribution */}
        <ChartCard title="Current Pipeline Distribution">
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={metrics.pipeline}
                dataKey="count"
                nameKey="state"
                cx="50%"
                cy="50%"
                outerRadius={90}
                label={({ state, count }: { state: string; count: number }) => `${state}: ${count}`}
                labelLine={false}
                fontSize={11}
              >
                {metrics.pipeline.map((entry, index) => (
                  <Cell key={entry.state} fill={entry.color || PIE_COLORS[index % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Resolution time */}
        {metrics.resolution_time && (
          <ChartCard title="Resolution Time">
            <div style={{ padding: '16px 0' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
                <TimeMetric label="Median" value={`${metrics.resolution_time.median_hours.toFixed(1)}h`} />
                <TimeMetric label="Mean" value={`${metrics.resolution_time.mean_hours.toFixed(1)}h`} />
                <TimeMetric label="P90" value={`${metrics.resolution_time.p90_hours.toFixed(1)}h`} />
              </div>
              <div style={{ marginTop: '16px', fontSize: '13px', color: '#6b7280', textAlign: 'center' }}>
                Based on {metrics.resolution_time.total_resolved} resolved issues
              </div>
            </div>
          </ChartCard>
        )}

        {/* ACU spend */}
        <ChartCard title="ACU Spend by Sizing">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={metrics.acu_spend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis
                dataKey="sizing"
                tick={{ fontSize: 11, fill: '#6b7280' }}
                tickFormatter={(v: string) => v === 'green' ? 'Small' : v === 'yellow' ? 'Medium' : 'Large'}
              />
              <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} />
              <Tooltip
                formatter={(value: number, name: string) => [
                  `${value.toFixed(1)} ACUs`,
                  name === 'avg_acus' ? 'Avg per issue' : 'Total',
                ]}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="avg_acus" fill="#3b82f6" name="Avg ACUs" radius={[4, 4, 0, 0]} />
              <Bar dataKey="total_acus" fill="#93c5fd" name="Total ACUs" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  )
}

interface MetricCardProps {
  label: string
  value: string
  color: string
}

function MetricCard({ label, value, color }: MetricCardProps) {
  return (
    <div style={{
      padding: '16px 20px',
      borderRadius: '8px',
      border: '1px solid #e5e7eb',
      backgroundColor: '#fff',
    }}>
      <div style={{ fontSize: '12px', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
        {label}
      </div>
      <div style={{ fontSize: '28px', fontWeight: 700, color, marginTop: '4px' }}>
        {value}
      </div>
    </div>
  )
}

interface ChartCardProps {
  title: string
  children: React.ReactNode
}

function ChartCard({ title, children }: ChartCardProps) {
  return (
    <div style={{
      padding: '16px 20px',
      borderRadius: '8px',
      border: '1px solid #e5e7eb',
      backgroundColor: '#fff',
    }}>
      <h3 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600, color: '#374151' }}>
        {title}
      </h3>
      {children}
    </div>
  )
}

interface TimeMetricProps {
  label: string
  value: string
}

function TimeMetric({ label, value }: TimeMetricProps) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: '24px', fontWeight: 700, color: '#111827' }}>{value}</div>
      <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '2px' }}>{label}</div>
    </div>
  )
}

export default Metrics
