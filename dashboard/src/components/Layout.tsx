import { Link, useLocation } from "react-router-dom"
import { cn } from "@/lib/utils"
import {
  LayoutDashboard,
  FileText,
  ClipboardList,
  Twitter,
  BarChart3,
  Settings,
  Newspaper,
} from "lucide-react"
import { ThemeToggle } from "./ThemeToggle"
import { SystemStatus } from "./SystemStatus"

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Events", href: "/events", icon: Newspaper },
  { name: "Outputs", href: "/outputs", icon: FileText },
  // { name: "Approved Queue", href: "/approved-queue", icon: ClipboardList }, // REMOVED: Users generate Twitter content directly from Outputs
  { name: "Generated Content", href: "/generated-content", icon: Twitter },
  { name: "Statistics", href: "/stats", icon: BarChart3 },
]

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-white dark:bg-[#1a1a1a]">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-[#242424] border-r border-gray-200 dark:border-gray-700">
        {/* Logo */}
        <div className="flex h-16 items-center gap-2 px-6 border-b border-gray-200 dark:border-gray-700">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">FA</span>
          </div>
          <span className="font-semibold text-lg text-gray-900 dark:text-white">FinAgent</span>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-1 p-4">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            return (
              <Link
                key={item.name}
                to={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-blue-50 dark:bg-blue-600/20 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-500/40"
                    : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/60 hover:text-gray-900 dark:hover:text-white"
                )}
              >
                <item.icon className="h-5 w-5" />
                {item.name}
              </Link>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-gray-700">
          {/* System Status */}
          <div className="mb-4 px-3">
            <SystemStatus />
          </div>

          <div className="flex items-center gap-2 mb-2">
            <Link
              to="/settings"
              className="flex-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/60 hover:text-gray-900 dark:hover:text-white transition-colors"
            >
              <Settings className="h-5 w-5" />
              Settings
            </Link>
            <ThemeToggle />
          </div>
          <div className="mt-2 px-3 text-xs text-gray-400 dark:text-gray-500">
            FinAgent v1.0.0 (MVP)
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="pl-64">
        <main className="p-8">
          {children}
        </main>
      </div>
    </div>
  )
}
