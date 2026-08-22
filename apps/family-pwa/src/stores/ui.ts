import { defineStore } from 'pinia'

export const useUiStore = defineStore('ui', {
  state: () => ({ activeTab: '概览', isOffline: !navigator.onLine, lastTrustedAt: '', careHistory: [] as Array<{ request_id: string; template: string; status: string; audit_time: string }>, viewedAlerts: [] as string[] }),
  actions: {
    selectTab(tab: string) { this.activeTab = tab }, setNetwork(value: boolean) { this.isOffline = value }, markTrusted(value: string) { this.lastTrustedAt = value },
    addCareHistory(item: { request_id: string; template: string; status: string; audit_time: string }) { if (!this.careHistory.some(x => x.request_id === item.request_id)) this.careHistory.unshift(item) },
    markAlertViewed(alertId: string) { if (!this.viewedAlerts.includes(alertId)) this.viewedAlerts.push(alertId) },
    clearSensitiveState() { this.activeTab = '概览'; this.isOffline = false; this.lastTrustedAt = ''; this.careHistory = []; this.viewedAlerts = [] }
  }
})
