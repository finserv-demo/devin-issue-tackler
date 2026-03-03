import { useMetrics } from '../api/hooks'
import { STATUS_CONFIG } from '../api/types'
import type { PipelineCount } from '../api/types'
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

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
        <MetricCard label="Resolved" value={String(metrics.total_done)} color="#16a34a" />
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
              <Line type="monotone" dataKey="resolved" stroke="#16a34a" strokeWidth={2} name="Resolved" />
              <Line type="monotone" dataKey="opened" stroke="#6b7280" strokeWidth={2} strokeDasharray="5 5" name="Opened" />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Pipeline distribution — horizontal stacked bar */}
        <ChartCard title="In-Flight Pipeline Distribution">
          <PipelineBar pipeline={metrics.pipeline} />
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

/** Horizontal stacked bar showing in-flight pipeline distribution.
 *  Earlier stages on the left, later on the right. Each segment is clickable
 *  and links to GitHub issues filtered by that label.
 */
function PipelineBar({ pipeline }: { pipeline: PipelineCount[] }) {
  const total = pipeline.reduce((sum, p) => sum + p.count, 0)
  if (total === 0) {
    return <div style={{ padding: '24px 0', textAlign: 'center', color: '#9ca3af', fontSize: '13px' }}>No in-flight issues</div>
  }

  return (
    <div>
      {/* Stacked bar */}
      <div style={{
        display: 'flex',
        height: '36px',
        borderRadius: '8px',
        overflow: 'hidden',
        marginBottom: '16px',
      }}>
        {pipeline.map((entry) => {
          const pct = (entry.count / total) * 100
          if (pct === 0) return null
          const config = STATUS_CONFIG[entry.state]
          return (
            <a
              key={entry.state}
              href={entry.github_filter_url}
              target="_blank"
              rel="noopener noreferrer"
              title={`${config?.label ?? entry.state}: ${entry.count} issue${entry.count !== 1 ? 's' : ''} — click to view on GitHub`}
              style={{
                width: `${pct}%`,
                backgroundColor: entry.color,
                minWidth: entry.count > 0 ? '24px' : 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                fontSize: '12px',
                fontWeight: 700,
                textDecoration: 'none',
                cursor: 'pointer',
                transition: 'filter 0.15s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.filter = 'brightness(0.85)' }}
              onMouseLeave={(e) => { e.currentTarget.style.filter = 'none' }}
            >
              {entry.count}
            </a>
          )
        })}
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', justifyContent: 'center' }}>
        {pipeline.map((entry) => {
          const config = STATUS_CONFIG[entry.state]
          return (
            <a
              key={entry.state}
              href={entry.github_filter_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                textDecoration: 'none',
                color: 'inherit',
                fontSize: '12px',
              }}
            >
              <span style={{
                width: '10px',
                height: '10px',
                borderRadius: '2px',
                backgroundColor: entry.color,
                display: 'inline-block',
              }} />
              <span style={{ color: '#374151', fontWeight: 500 }}>
                {config?.label ?? entry.state}
              </span>
              <span style={{ color: '#9ca3af' }}>
                {entry.count}
              </span>
            </a>
          )
        })}
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
