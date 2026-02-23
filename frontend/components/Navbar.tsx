'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'

export default function Navbar() {
  const pathname = usePathname()
  const router = useRouter()
  const [user, setUser] = useState<{ id: string; name: string; email: string } | null>(null)

  useEffect(() => {
    const load = () => {
      const raw = localStorage.getItem('medrix_user')
      setUser(raw ? JSON.parse(raw) : null)
    }
    load()
    window.addEventListener('medrix_auth_change', load)
    return () => window.removeEventListener('medrix_auth_change', load)
  }, [])

  const handleSignOut = () => {
    localStorage.removeItem('medrix_user')
    setUser(null)
    window.dispatchEvent(new Event('medrix_auth_change'))
    router.push('/signin')
  }

  const navItems = [
    { name: 'Home', href: '/', icon: '🏠' },
    { name: 'Upload', href: '/upload', icon: '📤' },
    { name: 'Documents', href: '/documents', icon: '📄' },
    { name: 'MediBot', href: '/ask', icon: '🤖' },
    { name: 'Medical ID', href: '/medical-id', icon: '💳' },
  ]

  return (
    <nav style={{ position: 'sticky', top: 0, zIndex: 50, background: 'rgba(255,251,247,0.92)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)', borderBottom: '1px solid rgba(249,115,22,0.12)', boxShadow: '0 1px 12px rgba(249,115,22,0.06)' }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '0 24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: '68px' }}>
          {/* Logo */}
          <Link href="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '34px', height: '34px', background: 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(249,115,22,0.3)' }}>
              <svg width="18" height="18" viewBox="0 0 16 16" fill="white">
                <rect x="6" y="1" width="4" height="14" rx="1.5"/>
                <rect x="1" y="6" width="14" height="4" rx="1.5"/>
              </svg>
            </div>
            <span style={{ fontSize: '22px', fontWeight: 900, background: 'linear-gradient(135deg, #1c1917 0%, #f97316 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text', letterSpacing: '0.02em' }}>
              Medrix
            </span>
          </Link>
          
          {/* Navigation Items */}
          <div style={{ display: 'flex', gap: '4px' }}>
            {navItems.map((item) => {
              const isActive = pathname === item.href || (pathname.startsWith(item.href) && item.href !== '/')
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  style={{
                    textDecoration: 'none',
                    padding: '9px 16px',
                    borderRadius: '10px',
                    fontSize: '14px',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    transition: 'all 0.2s ease',
                    background: isActive ? 'rgba(249,115,22,0.1)' : 'transparent',
                    border: isActive ? '1px solid rgba(249,115,22,0.25)' : '1px solid transparent',
                    color: isActive ? '#f97316' : '#78716c',
                    position: 'relative'
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'rgba(249,115,22,0.06)';
                      e.currentTarget.style.color = '#1c1917';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = '#78716c';
                    }
                  }}
                >
                  <span style={{ fontSize: '15px' }}>{item.icon}</span>
                  {item.name}
                  {isActive && (
                    <div style={{ position: 'absolute', bottom: '-2px', left: '16px', right: '16px', height: '2px', background: 'linear-gradient(90deg, #f97316 0%, #fb7185 100%)', borderRadius: '2px' }} />
                  )}
                </Link>
              )
            })}
          </div>
          
          {/* User Section */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {user ? (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 12px', background: 'rgba(249,115,22,0.08)', border: '1px solid rgba(249,115,22,0.2)', borderRadius: '10px' }}>
                  <div style={{ width: '28px', height: '28px', borderRadius: '8px', background: 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '13px', color: 'white', fontWeight: 700 }}>
                    {user.name ? user.name[0].toUpperCase() : '?'}
                  </div>
                  <span style={{ fontSize: '13px', fontWeight: 600, color: '#44403c', maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {user.name || user.email}
                  </span>
                </div>
                <button
                  onClick={handleSignOut}
                  style={{ padding: '8px 14px', background: 'transparent', border: '1.5px solid rgba(0,0,0,0.1)', borderRadius: '10px', fontSize: '13px', fontWeight: 600, color: '#78716c', cursor: 'pointer', transition: 'all 0.2s ease' }}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'rgba(239,68,68,0.4)'; e.currentTarget.style.color = '#dc2626'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'rgba(0,0,0,0.1)'; e.currentTarget.style.color = '#78716c'; }}
                >
                  Sign Out
                </button>
              </>
            ) : (
              <Link href="/signin" style={{ textDecoration: 'none' }}>
                <button
                  style={{ padding: '9px 18px', background: 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)', border: 'none', borderRadius: '10px', fontSize: '14px', fontWeight: 700, color: 'white', cursor: 'pointer', boxShadow: '0 4px 14px rgba(249,115,22,0.3)', transition: 'all 0.2s ease' }}
                  onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 6px 20px rgba(249,115,22,0.38)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 4px 14px rgba(249,115,22,0.3)'; }}
                >
                  Sign In
                </button>
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
