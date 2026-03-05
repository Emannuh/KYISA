import api from './client'

// ── Auth ─────────────────────────────────────────────────────────────────────
export const authAPI = {
  login: (email, password) => api.post('/auth/login/', { email, password }),
  logout: (refresh) => api.post('/auth/logout/', { refresh }),
  register: (data) => api.post('/auth/register/', data),
  refreshToken: (refresh) => api.post('/auth/token/refresh/', { refresh }),
  getProfile: () => api.get('/auth/profile/'),
  updateProfile: (data) => api.patch('/auth/profile/', data),
  changePassword: (data) => api.post('/auth/change-password/', data),
  listUsers: (params) => api.get('/auth/users/', { params }),
  getUser: (id) => api.get(`/auth/users/${id}/`),
  updateUser: (id, data) => api.patch(`/auth/users/${id}/`, data),
  deleteUser: (id) => api.delete(`/auth/users/${id}/`),
}

// ── Teams ────────────────────────────────────────────────────────────────────
export const teamsAPI = {
  list: (params) => api.get('/teams/', { params }),
  get: (id) => api.get(`/teams/${id}/`),
  create: (data) => api.post('/teams/', data),
  update: (id, data) => api.patch(`/teams/${id}/`, data),
  delete: (id) => api.delete(`/teams/${id}/`),
  // Players — supports both flat and nested patterns
  listPlayers: (teamIdOrParams) => {
    if (typeof teamIdOrParams === 'object') return api.get('/teams/players/', { params: teamIdOrParams })
    return api.get('/teams/players/', { params: { team: teamIdOrParams } })
  },
  getPlayer: (id) => api.get(`/teams/players/${id}/`),
  addPlayer: (teamId, data) => api.post('/teams/players/', { ...data, team: teamId }, {
    headers: data instanceof FormData ? { 'Content-Type': 'multipart/form-data' } : undefined,
  }),
  createPlayer: (data) => api.post('/teams/players/', data, {
    headers: data instanceof FormData ? { 'Content-Type': 'multipart/form-data' } : undefined,
  }),
  updatePlayer: (teamId, playerId, data) => api.patch(`/teams/players/${playerId}/`, data),
  deletePlayer: (teamId, playerId) => api.delete(`/teams/players/${playerId}/`),
}

// ── Competitions ─────────────────────────────────────────────────────────────
export const competitionsAPI = {
  list: (params) => api.get('/competitions/', { params }),
  get: (id) => api.get(`/competitions/${id}/`),
  create: (data) => api.post('/competitions/', data),
  update: (id, data) => api.patch(`/competitions/${id}/`, data),
  delete: (id) => api.delete(`/competitions/${id}/`),
  // Venues
  listVenues: (params) => api.get('/competitions/venues/', { params }),
  getVenue: (id) => api.get(`/competitions/venues/${id}/`),
  createVenue: (data) => api.post('/competitions/venues/', data),
  updateVenue: (id, data) => api.patch(`/competitions/venues/${id}/`, data),
  // Pools
  listPools: (params) => api.get('/competitions/pools/', { params }),
  getPool: (id) => api.get(`/competitions/pools/${id}/`),
  createPool: (data) => api.post('/competitions/pools/', data),
  // Pool Teams
  listPoolTeams: (params) => api.get('/competitions/pool-teams/', { params }),
  createPoolTeam: (data) => api.post('/competitions/pool-teams/', data),
  updatePoolTeam: (id, data) => api.patch(`/competitions/pool-teams/${id}/`, data),
  // Fixtures
  listFixtures: (params) => api.get('/competitions/fixtures/', { params }),
  getFixture: (id) => api.get(`/competitions/fixtures/${id}/`),
  updateFixture: (id, data) => api.patch(`/competitions/fixtures/${id}/`, data),
}

// ── Matches ──────────────────────────────────────────────────────────────────
export const matchesAPI = {
  listSquads: (params) => api.get('/matches/squads/', { params }),
  getSquad: (id) => api.get(`/matches/squads/${id}/`),
  createSquad: (data) => api.post('/matches/squads/', data),
  updateSquad: (id, data) => api.patch(`/matches/squads/${id}/`, data),
  listReports: (params) => api.get('/matches/reports/', { params }),
  getReport: (id) => api.get(`/matches/reports/${id}/`),
  createReport: (data) => api.post('/matches/reports/', data),
  updateReport: (id, data) => api.patch(`/matches/reports/${id}/`, data),
  listEvents: (params) => api.get('/matches/events/', { params }),
  createEvent: (data) => api.post('/matches/events/', data),
  deleteEvent: (id) => api.delete(`/matches/events/${id}/`),
  getStatistics: (params) => api.get('/matches/stats/', { params }),
  listStats: (params) => api.get('/matches/stats/', { params }),
}

// ── Referees ─────────────────────────────────────────────────────────────────
export const refereesAPI = {
  list: (params) => api.get('/referees/', { params }),
  listProfiles: (params) => api.get('/referees/', { params }),
  get: (id) => api.get(`/referees/${id}/`),
  approve: (id) => api.post(`/referees/${id}/approve/`),
  listAppointments: (params) => api.get('/referees/appointments/', { params }),
  createAppointment: (data) => api.post('/referees/appointments/', data),
  updateAppointment: (id, data) => api.patch(`/referees/appointments/${id}/`, data),
  listAvailability: (params) => api.get('/referees/availability/', { params }),
  setAvailability: (data) => api.post('/referees/availability/', data),
  listReviews: (params) => api.get('/referees/reviews/', { params }),
  createReview: (data) => api.post('/referees/reviews/', data),
}

// ── Portal API (new endpoints for React) ─────────────────────────────────────
export const portalAPI = {
  // Dashboard stats
  getDashboard: () => api.get('/portal/dashboard/'),
  getDashboardStats: () => api.get('/portal/dashboard/'),
  getAdminDashboard: () => api.get('/portal/admin/dashboard/'),

  // Verification / Clearance
  getClearanceRequests: (params) => api.get('/portal/clearance/', { params }),
  getClearanceDashboard: (params) => api.get('/portal/clearance/', { params }),
  getPlayerClearance: (id) => api.get(`/portal/clearance/${id}/`),
  approveClearance: (id) => api.post(`/portal/clearance/${id}/grant/`),
  rejectClearance: (id, data) => api.post(`/portal/clearance/${id}/reject/`, data),
  hudumVerify: (id, data) => api.post(`/portal/clearance/${id}/huduma/`, data),
  fifaCheck: (id, data) => api.post(`/portal/clearance/${id}/fifa-connect/`, data),
  grantClearance: (id) => api.post(`/portal/clearance/${id}/grant/`),
  revokeClearance: (id) => api.post(`/portal/clearance/${id}/revoke/`),
  iprsLookup: (nationalId) => api.post('/iprs/lookup/', { national_id: nationalId }),

  // Treasurer
  getTreasurerDashboard: () => api.get('/portal/treasurer/'),
  getTreasurerPayments: (params) => api.get('/portal/treasurer/payments/', { params }),
  verifyPayment: (id) => api.post(`/portal/treasurer/payments/${id}/verify/`),
  rejectPayment: (id) => api.post(`/portal/treasurer/payments/${id}/reject/`),
  confirmPayment: (teamId, data) => api.post(`/portal/treasurer/teams/${teamId}/confirm/`, data),

  // Admin
  getPendingRegistrations: () => api.get('/portal/admin/registrations/'),
  approveRegistration: (type, id, data) => api.post(`/portal/admin/registrations/${type}/${id}/approve/`, data),
  rejectRegistration: (type, id, data) => api.post(`/portal/admin/registrations/${type}/${id}/reject/`, data),
  getActivityLogs: (params) => api.get('/portal/admin/activity-logs/', { params }),
  undoAction: (logId) => api.post(`/portal/admin/activity-logs/${logId}/undo/`),
}

// ── Public API (no auth needed) ──────────────────────────────────────────────
export const publicAPI = {
  getHome: () => api.get('/public/home/'),
  getCompetitions: (params) => api.get('/public/competitions/', { params }),
  getCompetition: (id) => api.get(`/public/competitions/${id}/`),
  getResults: (params) => api.get('/public/results/', { params }),
  getStatistics: (params) => api.get('/public/statistics/', { params }),
  getStandings: (id) => api.get(`/public/standings/${id}/`),
}
