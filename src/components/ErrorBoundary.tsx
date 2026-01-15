import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-navy flex items-center justify-center p-4">
          <div className="bg-navy-light rounded-xl shadow-2xl p-8 max-w-2xl w-full border-2 border-red-500/30">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-12 h-12 bg-red-500/20 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-red-400" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-red-400">Something went wrong</h2>
                <p className="text-gray-400">An unexpected error occurred</p>
              </div>
            </div>

            {this.state.error && (
              <div className="mb-6">
                <details className="bg-navy/50 rounded-lg p-4 border border-white/10">
                  <summary className="text-yellow font-semibold cursor-pointer mb-2">
                    Error Details
                  </summary>
                  <pre className="text-sm text-gray-300 overflow-auto max-h-48 mt-2">
                    {this.state.error.toString()}
                    {this.state.errorInfo && (
                      <>
                        {'\n\n'}
                        {this.state.errorInfo.componentStack}
                      </>
                    )}
                  </pre>
                </details>
              </div>
            )}

            <div className="flex gap-4">
              <button
                onClick={this.handleReset}
                className="bg-yellow text-navy px-6 py-3 rounded-lg font-semibold hover:bg-yellow/90 transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={() => window.location.reload()}
                className="bg-navy-light border border-white/20 text-white px-6 py-3 rounded-lg font-semibold hover:bg-white/5 transition-colors"
              >
                Reload Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

