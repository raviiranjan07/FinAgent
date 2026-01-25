import { useState, useEffect } from "react"
import { X, AlertTriangle, Info, Eye, EyeOff } from "lucide-react"

interface EditContentModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (editedContent: string) => Promise<void>
  originalContent: string
  currentEditedContent?: string | null
  hashtags?: string[]
}

interface ValidationIssue {
  field: string
  code: string
  message: string
  phrase?: string
  position?: number
}

export function EditContentModal({
  isOpen,
  onClose,
  onSave,
  originalContent,
  currentEditedContent,
  hashtags = [],
}: EditContentModalProps) {
  const [editedContent, setEditedContent] = useState(currentEditedContent || originalContent)
  const [showOriginal, setShowOriginal] = useState(false)
  const [validationErrors, setValidationErrors] = useState<ValidationIssue[]>([])
  const [isSaving, setIsSaving] = useState(false)

  // Update content when props change
  useEffect(() => {
    setEditedContent(currentEditedContent || originalContent)
  }, [currentEditedContent, originalContent])

  // Character count validation
  const charCount = editedContent.length
  const isOverLimit = charCount > 280
  const isNearLimit = charCount >= 260

  const getCounterColor = () => {
    if (isOverLimit) return "text-red-600 dark:text-red-400 font-bold"
    if (isNearLimit) return "text-yellow-600 dark:text-yellow-400 font-semibold"
    return "text-gray-600 dark:text-gray-400"
  }

  const handleSave = async () => {
    // Clear previous errors
    setValidationErrors([])

    // Basic client-side validation
    const errors: ValidationIssue[] = []

    if (!editedContent.trim()) {
      errors.push({
        field: "edited_content",
        code: "empty_content",
        message: "Content cannot be empty",
      })
    }

    if (charCount > 280) {
      errors.push({
        field: "edited_content",
        code: "too_long",
        message: `Content exceeds 280 characters (current: ${charCount})`,
      })
    }

    if (errors.length > 0) {
      setValidationErrors(errors)
      return
    }

    // Save to backend
    setIsSaving(true)
    try {
      await onSave(editedContent)
      onClose()
    } catch (error: any) {
      // Handle backend validation errors
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
    setEditedContent(currentEditedContent || originalContent)
    setValidationErrors([])
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Edit X Content</h2>
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
              <div className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{originalContent}</div>
            </div>
          )}

          {/* Content Editor */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Edit Content</label>
              <span className={`text-sm ${getCounterColor()}`}>
                {charCount} / 280 characters
              </span>
            </div>
            <textarea
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              className={`w-full h-48 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 bg-white dark:bg-gray-900 text-gray-900 dark:text-white ${
                isOverLimit
                  ? "border-red-300 dark:border-red-700 focus:ring-red-500"
                  : "border-gray-300 dark:border-gray-600 focus:ring-blue-500"
              }`}
              placeholder="Enter your X content..."
              disabled={isSaving}
            />
            {isNearLimit && !isOverLimit && (
              <p className="mt-1 text-xs text-yellow-600 dark:text-yellow-400">
                Approaching character limit
              </p>
            )}
            {isOverLimit && (
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                Content exceeds X's 280 character limit
              </p>
            )}
          </div>

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
            disabled={isOverLimit || !editedContent.trim() || isSaving}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSaving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  )
}
