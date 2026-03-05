import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'

export default function NotFoundPage() {
  return (
    <>
      <Helmet><title>404 — KYISA</title></Helmet>
      <section className="min-h-[60vh] flex items-center justify-center">
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="text-center">
          <p className="text-8xl font-bold text-accent/20">404</p>
          <h1 className="text-2xl font-bold text-brand-50 mt-4">Page Not Found</h1>
          <p className="text-brand-300 mt-2 mb-6">The page you're looking for doesn't exist or has been moved.</p>
          <Link
            to="/"
            className="inline-flex px-6 py-2.5 bg-accent text-brand-900 font-semibold rounded-xl hover:bg-accent-light transition-colors"
          >
            Go Home
          </Link>
        </motion.div>
      </section>
    </>
  )
}
