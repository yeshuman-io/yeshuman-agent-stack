import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Input } from '../ui/input'
import { PageContainer } from '../ui/page-container'
import { Badge } from '../ui/badge'
import { Brain, Search, Loader2 } from 'lucide-react'
import { useMemories } from '../../hooks/use-memories'

export function MemoriesPage() {
  const { memories, isLoading, error } = useMemories()
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 20

  // Filter memories based on search term
  const filteredMemories = memories.filter(memory =>
    memory.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
    memory.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
    memory.subcategory.toLowerCase().includes(searchTerm.toLowerCase())
  )

  // Paginate results
  const totalPages = Math.ceil(filteredMemories.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const paginatedMemories = filteredMemories.slice(startIndex, startIndex + itemsPerPage)

  const getImportanceColor = (importance: string) => {
    switch (importance) {
      case 'high': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      case 'medium': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
      case 'low': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
    }
  }

  const getMemoryTypeColor = (type: string) => {
    switch (type) {
      case 'factual': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      case 'episodic': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
      case 'semantic': return 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200'
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
    }
  }

  if (isLoading) {
    return (
      <PageContainer>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span className="ml-2">Loading memories...</span>
        </div>
      </PageContainer>
    )
  }

  if (error) {
    return (
      <PageContainer>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Brain className="h-5 w-5 mr-2" />
              Memories
            </CardTitle>
            <CardDescription>Your stored memories and insights</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-red-600 dark:text-red-400">
              Failed to load memories: {error.message}
            </div>
          </CardContent>
        </Card>
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Brain className="h-5 w-5 mr-2" />
            Memories
          </CardTitle>
          <CardDescription>
            Your stored memories and insights ({filteredMemories.length} total)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Search */}
          <div className="mb-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search memories by content, category, or subcategory..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value)
                  setCurrentPage(1) // Reset to first page on search
                }}
                className="pl-10"
              />
            </div>
          </div>

          {/* Memories List */}
          <div className="space-y-4">
            {paginatedMemories.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                {searchTerm ? 'No memories match your search.' : 'No memories found.'}
              </div>
            ) : (
              paginatedMemories.map((memory) => (
                <div key={memory.id} className="border rounded-lg p-4 space-y-2">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-sm text-muted-foreground mb-2">
                        {new Date(memory.created_at).toLocaleDateString()} at{' '}
                        {new Date(memory.created_at).toLocaleTimeString()}
                      </p>
                      <p className="text-sm">{memory.content}</p>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Badge variant="secondary" className={getMemoryTypeColor(memory.memory_type)}>
                      {memory.memory_type}
                    </Badge>
                    <Badge variant="outline">
                      {memory.category}
                      {memory.subcategory && ` • ${memory.subcategory}`}
                    </Badge>
                    <Badge variant="secondary" className={getImportanceColor(memory.importance)}>
                      {memory.importance}
                    </Badge>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-6">
              <div className="text-sm text-muted-foreground">
                Showing {startIndex + 1} to {Math.min(startIndex + itemsPerPage, filteredMemories.length)} of {filteredMemories.length} memories
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-muted"
                >
                  Previous
                </button>
                <span className="px-3 py-1 text-sm">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                  disabled={currentPage === totalPages}
                  className="px-3 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-muted"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </PageContainer>
  )
}




