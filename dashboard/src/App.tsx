import { BrowserRouter, Routes, Route } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ThemeProvider } from "./contexts/ThemeContext"
import { Layout } from "./components/Layout"
import { Dashboard } from "./pages/Dashboard"
import { Outputs } from "./pages/Outputs"
import { Events } from "./pages/Events"
import { Stats } from "./pages/Stats"
// import ApprovedQueue from "./pages/ApprovedQueue"  // REMOVED: No longer needed
import { GeneratedContent } from "./pages/GeneratedContent"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      refetchOnWindowFocus: false,
    },
  },
})

function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/events" element={<Events />} />
              <Route path="/outputs" element={<Outputs />} />
              {/* <Route path="/approved-queue" element={<ApprovedQueue />} /> */}
              <Route path="/generated-content" element={<GeneratedContent />} />
              <Route path="/stats" element={<Stats />} />
            </Routes>
          </Layout>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  )
}

export default App
