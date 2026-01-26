import { useState, useEffect } from "react"
import { X, AlertTriangle, Info, Eye, EyeOff } from "lucide-react"

interface EditContentModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (editedContent: string) => Promise<void>
  originalContent: string
  currentEditedContent?: string | null
  hashtags?: string[]
  format?: "SINGLE" | "THREAD"  // NEW: format prop
}

interface ValidationIssue {
  field: string
  code: string
  message: string
  phrase?: string
  position?: number
}

// Helper to detect if content is a thread
function detectFormat(content: string): "SINGLE" | "THREAD" {
  try {
    const parsed = JSON.parse(content)
    // Check for wrapped format: {"format": "THREAD", "content": {"tweets": [...]}}
    if (parsed?.format === "THREAD") {
      return "THREAD"
    }
    // Check for simple array format (legacy)
    if (Array.isArray(parsed)) {
      return "THREAD"
    }
  } catch {
    // Not JSON, it's a single tweet
  }
  return "SINGLE"
}

// Helper to parse thread content - handles wrapped format
function parseThread(content: string): string[] {
  try {
    const parsed = JSON.parse(content)
    // Handle wrapped format: {"format": "THREAD", "content": {"tweets": [...]}}
    if (parsed?.content?.tweets && Array.isArray(parsed.content.tweets)) {
      return parsed.content.tweets
    }
    // Handle simple array format (legacy)
    if (Array.isArray(parsed)) {
      return parsed
    }
  } catch {
    // Not valid JSON
  }
  return [content]
}

// Helper to parse single tweet content
function parseSingle(content: string): string {
  try {
    const parsed = JSON.parse(content)
    // Handle wrapped format: {"format": "SINGLE", "content": {"tweet": "..."}}
    if (parsed?.content?.tweet) {
      return parsed.content.tweet
    }
  } catch {
    // Not valid JSON, return as-is
  }
  return content
}

export function EditContentModal({
  isOpen,
  onClose,
  onSave,
  originalContent,
  currentEditedContent,
  hashtags = [],
  format: formatProp,
}: EditContentModalProps) {
  // Auto-detect format from content if not provided
  const detectedFormat = formatProp || detectFormat(currentEditedContent || originalContent)

  // State for single tweet
  const [singleContent, setSingleContent] = useState("")

  // State for thread (array of tweets)
  const [threadContent, setThreadContent] = useState<string[]>([])

  const [showOriginal, setShowOriginal] = useState(false)
  const [validationErrors, setValidationErrors] = useState<ValidationIssue[]>([])
  const [isSaving, setIsSaving] = useState(false)

  // Initialize content based on format
  useEffect(() => {
    const content = currentEditedContent || originalContent

    if (detectedFormat === "THREAD") {
      setThreadContent(parseThread(content))
    } else {
      // Parse single content from wrapped format
      setSingleContent(parseSingle(content))
    }
  }, [currentEditedContent, originalContent, detectedFormat])

  // Get the content to save - use wrapped format
  const getContentToSave = (): string => {
    if (detectedFormat === "THREAD") {
      // Return wrapped format: {"format": "THREAD", "content": {"tweets": [...]}}
      return JSON.stringify({
        format: "THREAD",
        content: {
          tweets: threadContent
        }
      })
    }
    // Return wrapped format: {"format": "SINGLE", "content": {"tweet": "..."}}
    return JSON.stringify({
      format: "SINGLE",
      content: {
        tweet: singleContent
      }
    })
  }

  // Validate content
  const validateContent = (): ValidationIssue[] => {
    const errors: ValidationIssue[] = []

    if (detectedFormat === "THREAD") {
      // Validate each tweet in thread
      threadContent.forEach((tweet, idx) => {
        if (!tweet.trim()) {
          errors.push({
            field: `tweet_${idx + 1}`,
            code: "empty_tweet",
            message: `Tweet ${idx + 1}: Cannot be empty`,
          })
        } else if (tweet.length > 280) {
          errors.push({
            field: `tweet_${idx + 1}`,
            code: "too_long",
            message: `Tweet ${idx + 1}: Exceeds 280 characters (${tweet.length} chars)`,
          })
        }
      })
    } else {
      // Validate single tweet
      if (!singleContent.trim()) {
        errors.push({
          field: "edited_content",
          code: "empty_content",
          message: "Content cannot be empty",
        })
      } else if (singleContent.length > 280) {
        errors.push({
          field: "edited_content",
          code: "too_long",
          message: `Content exceeds 280 characters (current: ${singleContent.length})`,
        })
      }
    }

    return errors
  }

  const handleSave = async () => {
    setValidationErrors([])

    // Client-side validation
    const errors = validateContent()
    if (errors.length > 0) {
      setValidationErrors(errors)
      return
    }

    // Save to backend
    setIsSaving(true)
    try {
      await onSave(getContentToSave())
      onClose()
    } catch (error: any) {
      if (error.response?.data?.error === "validation_failed") {
        setValidationErrors(error.response.data.issues)
      } else {
        setValidationErrors([
          {
            field: "general",
            code: "save_failed",
            message: error.response?.data?.detail || "Failed to save changes",
          },
        ])
      }
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    const content = currentEditedContent || originalContent
    if (detectedFormat === "THREAD") {
      setThreadContent(parseThread(content))
    } else {
      setSingleContent(content)
    }
    setValidationErrors([])
    onClose()
  }

  // Update a specific tweet in thread
  const updateTweet = (index: number, value: string) => {
    const newThread = [...threadContent]
    newThread[index] = value
    setThreadContent(newThread)
  }

  // Get character count color
  const getCounterColor = (count: number) => {
    if (count > 280) return "text-red-600 dark:text-red-400 font-bold"
    if (count >= 260) return "text-yellow-600 dark:text-yellow-400 font-semibold"
    return "text-gray-600 dark:text-gray-400"
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Edit X {detectedFormat === "THREAD" ? "Thread" : "Content"}
          </h2>
          <button
            onClick={handleCancel}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            disabled={isSaving}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-4 space-y-4">
          {/* Safety Warning */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3 flex gap-2">
            <Info className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-700 dark:text-blue-300">
              <strong>Safety reminder:</strong> Do not include investment advice, predictions, or phrases like "buy",
              "sell", "guaranteed returns", etc.
            </div>
          </div>

          {/* Validation Errors */}
          {validationErrors.length > 0 && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
              <div className="flex gap-2">
                <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  {validationErrors.map((error, idx) => (
                    <div key={idx} className="text-sm text-red-700 dark:text-red-300">
                      {error.message}
                      {error.phrase && <span className="font-mono ml-1">"{error.phrase}"</span>}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Show Original Toggle */}
          {currentEditedContent && (
            <button
              onClick={() => setShowOriginal(!showOriginal)}
              className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 hover:underline"
            >
              {showOriginal ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              {showOriginal ? "Hide" : "Show"} Original Content
            </button>
          )}

          {/* Original Content Display */}
          {showOriginal && (
            <div className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-3">
              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Original Content:</div>
              <div className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                {detectedFormat === "THREAD"
                  ? parseThread(originalContent).map((tweet, i) => (
                      <div key={i} className="mb-2 pb-2 border-b border-gray-200 dark:border-gray-600 last:border-0">
                        <span className="font-medium">Tweet {i + 1}:</span> {tweet}
                      </div>
                    ))
                  : originalContent
                }
              </div>
            </div>
          )}

          {/* Content Editor - SINGLE */}
          {detectedFormat === "SINGLE" && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <label htmlFor="edit-content-single" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Edit Content</label>
                <span className={`text-sm ${getCounterColor(singleContent.length)}`}>
                  {singleContent.length} / 280 characters
                </span>
              </div>
              <textarea
                id="edit-content-single"
                name="edit-content-single"
                value={singleContent}
                onChange={(e) => setSingleContent(e.target.value)}
                className={`w-full h-48 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 bg-white dark:bg-gray-900 text-gray-900 dark:text-white ${
                  singleContent.length > 280
                    ? "border-red-300 dark:border-red-700 focus:ring-red-500"
                    : "border-gray-300 dark:border-gray-600 focus:ring-blue-500"
                }`}
                placeholder="Enter your X content..."
                disabled={isSaving}
              />
              {singleContent.length >= 260 && singleContent.length <= 280 && (
                <p className="mt-1 text-xs text-yellow-600 dark:text-yellow-400">
                  Approaching character limit
                </p>
              )}
              {singleContent.length > 280 && (
                <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                  Content exceeds X's 280 character limit
                </p>
              )}
            </div>
          )}

          {/* Content Editor - THREAD */}
          {detectedFormat === "THREAD" && (
            <div className="space-y-4">
              <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Edit Thread ({threadContent.length} tweets)
              </div>
              {threadContent.map((tweet, index) => (
                <div key={index} className="border border-gray-200 dark:border-gray-700 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <label htmlFor={`edit-thread-tweet-${index + 1}`} className="text-sm font-medium text-gray-600 dark:text-gray-400">
                      Tweet {index + 1}/{threadContent.length}
                    </label>
                    <span className={`text-sm ${getCounterColor(tweet.length)}`}>
                      {tweet.length} / 280
                    </span>
                  </div>
                  <textarea
                    id={`edit-thread-tweet-${index + 1}`}
                    name={`edit-thread-tweet-${index + 1}`}
                    value={tweet}
                    onChange={(e) => updateTweet(index, e.target.value)}
                    className={`w-full h-28 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 bg-white dark:bg-gray-900 text-gray-900 dark:text-white ${
                      tweet.length > 280
                        ? "border-red-300 dark:border-red-700 focus:ring-blue-500"
                        : "border-gray-300 dark:border-gray-600 focus:ring-blue-500"
                    }`}
                    placeholder={`Tweet ${index + 1}...`}
                    disabled={isSaving}
                  />
                  {tweet.length > 280 && (
                    <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                      Exceeds 280 character limit
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Hashtags Display */}
          {hashtags.length > 0 && (
            <div>
              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Suggested Hashtags:</div>
              <div className="flex flex-wrap gap-2">
                {hashtags.map((tag, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={handleCancel}
            disabled={isSaving}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSaving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  )
}
