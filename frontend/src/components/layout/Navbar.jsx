import { Link, useLocation } from 'react-router-dom'
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Bars3Icon, XMarkIcon, UserCircleIcon } from '@heroicons/react/24/outline'
import { useAuth } from '../../contexts/AuthContext'

const publicLinks = [
  { to: '/', label: 'Home' },
  { to: '/competitions', label: 'Competitions' },
  { to: '/results', label: 'Results' },
  { to: '/statistics', label: 'Statistics' },
  { to: '/about', label: 'About' },
  { to: '/contact', label: 'Contact' },
]

export default function Navbar() {
  const { isAuthenticated, user, logout } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  const isPortal = location.pathname.startsWith('/portal')
  if (isPortal) return null // Portal uses sidebar, not navbar

  return (
    <nav className="fixed top-0 inset-x-0 z-50 glass">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="h-9 w-9 rounded-lg bg-accent flex items-center justify-center text-brand-900 font-bold text-sm">
              K
            </div>
            <div>
              <span className="text-lg font-bold text-brand-50 group-hover:text-accent transition-colors">
                KYISA
              </span>
              <span className="hidden sm:block text-[10px] text-brand-300 leading-none -mt-0.5">
                11th Edition — 2026
              </span>
            </div>
          </Link>

          {/* Desktop Links */}
          <div className="hidden md:flex items-center gap-1">
            {publicLinks.map(({ to, label }) => (
              <Link
                key={to}
                to={to}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  location.pathname === to
                    ? 'text-accent bg-accent/10'
                    : 'text-brand-200 hover:text-brand-50 hover:bg-brand-700'
                }`}
              >
                {label}
              </Link>
            ))}
          </div>

          {/* Right side */}
          <div className="flex items-center gap-3">
            {isAuthenticated ? (
              <div className="hidden md:flex items-center gap-3">
                <Link
                  to="/portal"
                  className="px-4 py-2 bg-accent text-brand-900 font-semibold text-sm rounded-lg hover:bg-accent-light transition-colors"
                >
                  Dashboard
                </Link>
                <button
                  onClick={logout}
                  className="px-3 py-2 text-sm text-brand-200 hover:text-brand-50 hover:bg-brand-700 rounded-lg transition-colors"
                >
                  Logout
                </button>
              </div>
            ) : (
              <div className="hidden md:flex items-center gap-2">
                <Link
                  to="/register/team"
                  className="px-3 py-2 text-sm text-brand-200 hover:text-brand-50 hover:bg-brand-700 rounded-lg transition-colors"
                >
                  Register Team
                </Link>
                <Link
                  to="/login"
                  className="px-4 py-2 bg-accent text-brand-900 font-semibold text-sm rounded-lg hover:bg-accent-light transition-colors"
                >
                  Sign In
                </Link>
              </div>
            )}

            {/* Mobile toggle */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden p-2 rounded-lg hover:bg-brand-700 text-brand-200"
            >
              {mobileOpen ? <XMarkIcon className="h-6 w-6" /> : <Bars3Icon className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden border-t border-border bg-brand-800"
          >
            <div className="px-4 py-3 space-y-1">
              {publicLinks.map(({ to, label }) => (
                <Link
                  key={to}
                  to={to}
                  onClick={() => setMobileOpen(false)}
                  className={`block px-3 py-2 rounded-lg text-sm font-medium ${
                    location.pathname === to ? 'text-accent bg-accent/10' : 'text-brand-200'
                  }`}
                >
                  {label}
                </Link>
              ))}
              <div className="pt-3 border-t border-border space-y-1">
                {isAuthenticated ? (
                  <>
                    <Link to="/portal" onClick={() => setMobileOpen(false)}
                      className="block px-3 py-2 text-sm font-medium text-accent">
                      Dashboard
                    </Link>
                    <button onClick={() => { logout(); setMobileOpen(false) }}
                      className="block w-full text-left px-3 py-2 text-sm text-brand-200">
                      Logout
                    </button>
                  </>
                ) : (
                  <>
                    <Link to="/login" onClick={() => setMobileOpen(false)}
                      className="block px-3 py-2 text-sm font-semibold text-accent">
                      Sign In
                    </Link>
                    <Link to="/register/team" onClick={() => setMobileOpen(false)}
                      className="block px-3 py-2 text-sm text-brand-200">
                      Register Team
                    </Link>
                  </>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  )
}
