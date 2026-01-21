import { BrowserRouter, Routes, Route } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Layout } from "./components/Layout"
import { Dashboard } from "./pages/Dashboard"
import { Outputs } from "./pages/Outputs"
import { Evaluations } from "./pages/Evaluations"
import { Stats } from "./pages/Stats"

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
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/outputs" element={<Outputs />} />
            <Route path="/evaluations" element={<Evaluations />} />
            <Route path="/stats" element={<Stats />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
