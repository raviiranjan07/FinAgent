import { useQuery } from '@tanstack/react-query';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react';

interface QuotaInfo {
  available: boolean;
  time_until_reset: string;
  last_429_at: string | null;
  last_429_at_ist: string | null;
  reset_at_ist: string | null;
}

interface SystemStatusResponse {
  status: string;
  content_generation_enabled: boolean;
  publishing_enabled: boolean;
  prompt_version: string;
  twitter_prompt_version: string;
  llm_mode_configured: string;
  llm_mode_active: string;
  quota_status: {
    groq: QuotaInfo;
    gemini_primary: QuotaInfo;
    gemini_secondary: QuotaInfo;
    ollama: QuotaInfo;
  };
  timestamp: string;
}

export function SystemStatus() {
  const { data: status, isLoading } = useQuery<SystemStatusResponse>({
    queryKey: ['system-status'],
    queryFn: async () => {
      const res = await fetch('http://localhost:8001/api/system/status');
      if (!res.ok) throw new Error('Failed to fetch system status');
      return res.json();
    },
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  if (isLoading || !status) {
    return null;
  }

  const hasIssues = !status.content_generation_enabled || !status.publishing_enabled;

  const isFallbackMode = status.llm_mode_configured !== status.llm_mode_active;

  return (
    <div className="space-y-2 text-xs">
      {/* Header */}
      <div className="font-semibold text-gray-700 dark:text-gray-300 mb-2">
        System Status
      </div>

      {/* Active LLM Mode */}
      <div className="flex items-center justify-between">
        <span className="text-gray-600 dark:text-gray-400">LLM:</span>
        <Badge
          variant={isFallbackMode ? "destructive" : "default"}
          className="text-xs"
        >
          {status.llm_mode_active.toUpperCase()}
        </Badge>
      </div>

      {/* Quota Status - Vertical */}
      <div className="space-y-1 pt-1">
        {/* Gemini Primary */}
        <div className="flex items-center justify-between">
          <span className="text-gray-600 dark:text-gray-400">Gemini 1°:</span>
          <div className="flex items-center gap-1">
            {status.quota_status.gemini_primary?.available ? (
              <CheckCircle className="h-3 w-3 text-green-500" />
            ) : (
              <>
                <XCircle className="h-3 w-3 text-red-500" />
                <span className="text-xs text-red-600">
                  {status.quota_status.gemini_primary?.time_until_reset || 'N/A'}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Gemini Secondary */}
        <div className="flex items-center justify-between">
          <span className="text-gray-600 dark:text-gray-400">Gemini 2°:</span>
          <div className="flex items-center gap-1">
            {status.quota_status.gemini_secondary?.available ? (
              <CheckCircle className="h-3 w-3 text-green-500" />
            ) : (
              <>
                <XCircle className="h-3 w-3 text-red-500" />
                <span className="text-xs text-red-600">
                  {status.quota_status.gemini_secondary?.time_until_reset || 'N/A'}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Groq */}
        <div className="flex items-center justify-between">
          <span className="text-gray-600 dark:text-gray-400">Groq:</span>
          <div className="flex items-center gap-1">
            {status.quota_status.groq?.available ? (
              <CheckCircle className="h-3 w-3 text-green-500" />
            ) : (
              <>
                <XCircle className="h-3 w-3 text-red-500" />
                <span className="text-xs text-red-600">
                  {status.quota_status.groq?.time_until_reset || 'N/A'}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Ollama */}
        <div className="flex items-center justify-between">
          <span className="text-gray-600 dark:text-gray-400">Ollama:</span>
          <CheckCircle className="h-3 w-3 text-green-500" />
        </div>
      </div>

      {/* Fallback Warning */}
      {isFallbackMode && (
        <div className="pt-2 text-xs text-yellow-600 dark:text-yellow-500">
          ⚠️ Fallback mode
        </div>
      )}

      {/* Issues Warning */}
      {hasIssues && (
        <div className="pt-2 space-y-1">
          {!status.content_generation_enabled && (
            <div className="text-xs text-red-600 dark:text-red-500">
              ⚠️ Generation disabled
            </div>
          )}
          {!status.publishing_enabled && (
            <div className="text-xs text-red-600 dark:text-red-500">
              🛑 Publishing disabled
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function SystemStatusBanner() {
  const { data: status } = useQuery<SystemStatusResponse>({
    queryKey: ['system-status'],
    queryFn: async () => {
      const res = await fetch('http://localhost:8001/api/system/status');
      if (!res.ok) throw new Error('Failed to fetch system status');
      return res.json();
    },
    refetchInterval: 30000,
  });

  if (!status) return null;

  const hasIssues = !status.content_generation_enabled || !status.publishing_enabled;

  if (!hasIssues) return null;

  return (
    <Alert variant="destructive" className="mb-4">
      <AlertTriangle className="h-4 w-4" />
      <AlertDescription className="ml-2">
        <div className="font-semibold">System Status Alert</div>
        {!status.content_generation_enabled && (
          <div className="mt-1">⚠️ Content generation is currently <strong>DISABLED</strong></div>
        )}
        {!status.publishing_enabled && (
          <div className="mt-1">🛑 Publishing is currently <strong>DISABLED</strong></div>
        )}
      </AlertDescription>
    </Alert>
  );
}
