import { Component, type ReactNode } from "react"
import { copy } from "../lib/copy"

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log error for debugging (could send to error reporting service)
    console.error("ErrorBoundary caught an error:", error, errorInfo)
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null })
  }

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <main className="min-h-screen page-fade">
          <div className="mx-auto max-w-2xl px-6 py-16">
            <h1 className="text-xl font-semibold text-slate-100 mb-4">
              Something went wrong
            </h1>
            <p className="text-sm text-slate-300 mb-6">
              {copy.global.errors.missingDataset}
            </p>
            {this.state.error && (
              <details className="mb-6">
                <summary className="text-xs text-slate-400 cursor-pointer hover:text-slate-300">
                  Technical details
                </summary>
                <pre className="mt-2 p-3 bg-slate-800/50 rounded text-xs text-slate-400 overflow-auto max-h-40">
                  {this.state.error.message}
                </pre>
              </details>
            )}
            <div className="flex gap-3">
              <button
                onClick={this.handleReset}
                className="px-4 py-2 text-sm bg-slate-700 hover:bg-slate-600 text-slate-200 rounded transition-colors"
              >
                Try again
              </button>
              <a
                href="/"
                className="px-4 py-2 text-sm bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition-colors"
              >
                Go home
              </a>
            </div>
          </div>
        </main>
      )
    }

    return this.props.children
  }
}
