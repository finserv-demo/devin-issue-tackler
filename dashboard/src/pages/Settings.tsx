import { useState, useEffect } from 'react'
import { useSettings, useUpdateSettings } from '../api/hooks'
import type { SettingsData } from '../api/types'

function Settings() {
  const { data: settings, isLoading, error } = useSettings()
  const updateSettings = useUpdateSettings()
  const [form, setForm] = useState<Partial<SettingsData>>({})
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    if (settings) {
      setForm(settings)
      setDirty(false)
    }
  }, [settings])

  const handleChange = (key: keyof SettingsData, value: string | number) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    setDirty(true)
  }

  const handleSave = () => {
    updateSettings.mutate(form, {
      onSuccess: () => setDirty(false),
    })
  }

  if (isLoading) {
    return <div style={{ padding: '2rem', textAlign: 'center', color: '#6b7280' }}>Loading settings...</div>
  }

  if (error) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#dc2626' }}>
        Failed to load settings: {error.message}
      </div>
    )
  }

  return (
    <div style={{ maxWidth: '640px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '22px', color: '#111827' }}>Settings</h1>
        <button
          onClick={handleSave}
          disabled={!dirty || updateSettings.isPending}
          style={{
            padding: '8px 20px',
            borderRadius: '6px',
            border: 'none',
            backgroundColor: dirty ? '#2563eb' : '#93c5fd',
            color: '#fff',
            fontSize: '13px',
            fontWeight: 600,
            cursor: dirty && !updateSettings.isPending ? 'pointer' : 'not-allowed',
          }}
        >
          {updateSettings.isPending ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      {updateSettings.isSuccess && (
        <div style={{
          marginBottom: '16px',
          padding: '8px 12px',
          borderRadius: '6px',
          backgroundColor: '#dcfce7',
          color: '#16a34a',
          fontSize: '13px',
        }}>
          Settings saved successfully.
        </div>
      )}

      {/* General section */}
      <SettingsSection title="General">
        <SettingsField label="Target Repository" hint="The GitHub repository being automated">
          <input
            type="text"
            value={String(form.target_repo ?? '')}
            disabled
            style={inputStyle}
          />
        </SettingsField>
        <SettingsField label="Opt-out Label" hint="Issues with this label will be skipped">
          <input
            type="text"
            value={String(form.opt_out_label ?? '')}
            onChange={(e) => handleChange('opt_out_label', e.target.value)}
            style={inputStyle}
          />
        </SettingsField>
      </SettingsSection>

      {/* ACU Budgets */}
      <SettingsSection title="ACU Budgets">
        <SettingsField label="Triage ACU Limit" hint="Maximum ACUs per triage session">
          <input
            type="number"
            value={form.acu_limit_triage ?? 0}
            onChange={(e) => handleChange('acu_limit_triage', parseInt(e.target.value) || 0)}
            style={inputStyle}
            min={1}
          />
        </SettingsField>
        <SettingsField label="Implement ACU Limit" hint="Maximum ACUs per implementation session">
          <input
            type="number"
            value={form.acu_limit_implement ?? 0}
            onChange={(e) => handleChange('acu_limit_implement', parseInt(e.target.value) || 0)}
            style={inputStyle}
            min={1}
          />
        </SettingsField>
      </SettingsSection>

      {/* Concurrency */}
      <SettingsSection title="Concurrency">
        <SettingsField label="Max Concurrent Implement Sessions" hint="Parallel implementation sessions">
          <input
            type="number"
            value={form.max_concurrent_implement ?? 0}
            onChange={(e) => handleChange('max_concurrent_implement', parseInt(e.target.value) || 0)}
            style={inputStyle}
            min={1}
            max={50}
          />
        </SettingsField>
        <SettingsField label="Max Concurrent Total Sessions" hint="Total parallel sessions (triage + implement)">
          <input
            type="number"
            value={form.max_concurrent_total ?? 0}
            onChange={(e) => handleChange('max_concurrent_total', parseInt(e.target.value) || 0)}
            style={inputStyle}
            min={1}
            max={100}
          />
        </SettingsField>
      </SettingsSection>

      {/* Polling & Rate Limits */}
      <SettingsSection title="Polling & Rate Limits">
        <SettingsField label="Polling Interval (seconds)" hint="How often to check session status">
          <input
            type="number"
            value={form.polling_interval_seconds ?? 0}
            onChange={(e) => handleChange('polling_interval_seconds', parseInt(e.target.value) || 0)}
            style={inputStyle}
            min={5}
            max={300}
          />
        </SettingsField>
        <SettingsField label="Bulk Triage Rate Limit" hint="Max issues to triage per minute">
          <input
            type="number"
            value={form.bulk_triage_rate_limit ?? 0}
            onChange={(e) => handleChange('bulk_triage_rate_limit', parseInt(e.target.value) || 0)}
            style={inputStyle}
            min={1}
            max={60}
          />
        </SettingsField>
      </SettingsSection>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px 12px',
  borderRadius: '6px',
  border: '1px solid #d1d5db',
  fontSize: '13px',
  fontFamily: 'inherit',
  outline: 'none',
  boxSizing: 'border-box',
}

interface SettingsSectionProps {
  title: string
  children: React.ReactNode
}

function SettingsSection({ title, children }: SettingsSectionProps) {
  return (
    <div style={{
      marginBottom: '24px',
      padding: '16px 20px',
      borderRadius: '8px',
      border: '1px solid #e5e7eb',
      backgroundColor: '#fff',
    }}>
      <h3 style={{ margin: '0 0 16px', fontSize: '14px', fontWeight: 600, color: '#374151' }}>
        {title}
      </h3>
      {children}
    </div>
  )
}

interface SettingsFieldProps {
  label: string
  hint: string
  children: React.ReactNode
}

function SettingsField({ label, hint, children }: SettingsFieldProps) {
  return (
    <div style={{ marginBottom: '14px' }}>
      <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: '#374151', marginBottom: '4px' }}>
        {label}
      </label>
      <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '6px' }}>{hint}</div>
      {children}
    </div>
  )
}

export default Settings
