'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { 
  HomeIcon, 
  DocumentPlusIcon, 
  ClockIcon, 
  ChatBubbleLeftRightIcon,
  IdentificationIcon 
} from '@heroicons/react/24/outline'

export default function Navbar() {
  const pathname = usePathname()

  const navItems = [
    { name: 'Home', href: '/', icon: HomeIcon },
    { name: 'Upload', href: '/upload', icon: DocumentPlusIcon },
    { name: 'Documents', href: '/documents', icon: DocumentPlusIcon },
    { name: 'Timeline', href: '/timeline', icon: ClockIcon },
    { name: 'Knowledge Graph', href: '/knowledge-graph', icon: HomeIcon },
    { name: 'Ask AI', href: '/ask', icon: ChatBubbleLeftRightIcon },
    { name: 'Medical ID', href: '/medical-id', icon: IdentificationIcon },
  ]

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <Link href="/" className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">
                Medrix
              </Link>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              {navItems.map((item) => {
                const Icon = item.icon
                const isActive = pathname === item.href
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                      isActive
                        ? 'border-blue-500 text-gray-900'
                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                    }`}
                  >
                    <Icon className="h-5 w-5 mr-1" />
                    {item.name}
                  </Link>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </nav>
  )
}
