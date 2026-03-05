import { Outlet } from 'react-router-dom'
import Navbar from './Navbar'

export default function PublicLayout() {
  return (
    <div className="min-h-screen bg-brand-900">
      <Navbar />
      <main className="pt-16">
        <Outlet />
      </main>
      {/* Footer */}
      <footer className="border-t border-border bg-brand-800 mt-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="h-8 w-8 rounded-lg bg-accent flex items-center justify-center text-brand-900 font-bold text-xs">K</div>
                <span className="text-lg font-bold text-brand-50">KYISA</span>
              </div>
              <p className="text-sm text-brand-300">
                Kenya Youth Intercounty Sports Association — 11th Edition, 2026 Season.
              </p>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-brand-50 mb-3">Quick Links</h4>
              <ul className="space-y-2 text-sm text-brand-300">
                <li><a href="/competitions" className="hover:text-accent transition-colors">Competitions</a></li>
                <li><a href="/results" className="hover:text-accent transition-colors">Results</a></li>
                <li><a href="/statistics" className="hover:text-accent transition-colors">Statistics</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-brand-50 mb-3">Registration</h4>
              <ul className="space-y-2 text-sm text-brand-300">
                <li><a href="/register/team" className="hover:text-accent transition-colors">Register Team</a></li>
                <li><a href="/register/referee" className="hover:text-accent transition-colors">Register as Referee</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-brand-50 mb-3">Contact</h4>
              <ul className="space-y-2 text-sm text-brand-300">
                <li>info@kyisa.ke</li>
                <li>Nairobi, Kenya</li>
              </ul>
            </div>
          </div>
          <div className="mt-8 pt-6 border-t border-border text-center text-xs text-brand-400">
            © 2026 KYISA. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  )
}
