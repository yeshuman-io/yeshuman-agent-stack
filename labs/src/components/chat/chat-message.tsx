import { useState } from 'react';
import { Bot, User, Plane, Leaf, Heart, ThumbsUp, ThumbsDown } from 'lucide-react';
import type { ChatMessage as ChatMessageType } from '../../types';
import { CURRENT_CLIENT } from '../../constants';

// Helper function to get the appropriate icon component
const getBrandIcon = (iconName: string) => {
  switch (iconName) {
    case 'Bot':
      return Bot;
    case 'Plane':
      return Plane;
    case 'Leaf':
      return Leaf;
    case 'Heart':
      return Heart;
    default:
      return Bot; // fallback to Bot
  }
};

const POSITIVE_TAGS = ['Helpful', 'Clear', 'Grounded', 'Actionable', 'Respectful'];
const NEGATIVE_TAGS = ['Incorrect', 'Off-topic', 'Unhelpful', 'Hallucinated', 'Unsafe'];

interface ChatMessageProps {
  message: ChatMessageType;
  onFeedback?: (runId: string, score?: number, tags?: string[], comment?: string) => void;
}

export const ChatMessage = ({ message, onFeedback }: ChatMessageProps) => {
  const [showFeedback, setShowFeedback] = useState(false);
  const [selectedScore, setSelectedScore] = useState<number | null>(null);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Check if feedback can be shown
  const canShowFeedback = !message.isUser && message.runId && onFeedback;
  
  // Debug logging
  console.log('ChatMessage render:', {
    messageId: message.id,
    isUser: message.isUser,
    hasRunId: !!message.runId,
    runId: message.runId,
    hasOnFeedback: !!onFeedback,
    canShowFeedback
  });

  const handleVote = (score: number) => {
    console.log('🎯 [FEEDBACK UI] Vote clicked:', { score, runId: message.runId });
    setSelectedScore(score);
    setShowFeedback(true);
  };

  const handleTagToggle = (tag: string) => {
    setSelectedTags(prev => 
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    );
  };

  const handleSubmit = async () => {
    if (!message.runId || !onFeedback || selectedScore === null) return;
    
    console.log('📤 [FEEDBACK UI] Submitting:', { 
      runId: message.runId, 
      score: selectedScore, 
      tags: selectedTags, 
      comment 
    });
    
    setIsSubmitting(true);
    await onFeedback(message.runId, selectedScore, selectedTags.length > 0 ? selectedTags : undefined, comment || undefined);
    setIsSubmitting(false);
    setShowFeedback(false);
    setSelectedScore(null);
    setSelectedTags([]);
    setComment('');
  };

  const handleSkip = async () => {
    if (!message.runId || !onFeedback || selectedScore === null) return;
    
    console.log('⏭️ [FEEDBACK UI] Skipping details, just submitting score');
    setIsSubmitting(true);
    await onFeedback(message.runId, selectedScore);
    setIsSubmitting(false);
    setShowFeedback(false);
    setSelectedScore(null);
    setSelectedTags([]);
    setComment('');
  };

  const handleCancel = () => {
    setShowFeedback(false);
    setSelectedScore(null);
    setSelectedTags([]);
    setComment('');
  };

  const availableTags = selectedScore === 1 ? POSITIVE_TAGS : NEGATIVE_TAGS;

  return (
    <div className={`flex gap-3 ${message.isUser ? 'flex-row-reverse' : ''}`}>
      <div className="w-8 h-8 rounded-full flex items-center justify-center bg-muted text-muted-foreground">
        {message.isUser ? (
          <User className="h-4 w-4" />
        ) : (
          (() => {
            const IconComponent = getBrandIcon(CURRENT_CLIENT.brandIcon || 'Bot');
            return <IconComponent className="h-4 w-4" />;
          })()
        )}
      </div>
      <div className="flex-1">
        <div className="bg-muted/50 rounded-lg p-3">
          <div className="whitespace-pre-wrap text-sm">
            {message.content}
          </div>
        </div>
        
        {/* Feedback controls for AI messages */}
        {canShowFeedback && (
          <div className="flex gap-2 mt-2">
            <button
              onClick={() => handleVote(1)}
              className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-green-600 transition-colors"
              title="Helpful"
            >
              <ThumbsUp className="h-4 w-4" />
            </button>
            <button
              onClick={() => handleVote(0)}
              className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-red-600 transition-colors"
              title="Not helpful"
            >
              <ThumbsDown className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Feedback detail popover */}
        {showFeedback && canShowFeedback && (
          <div className="mt-2 p-3 bg-background border rounded-lg shadow-lg">
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium">Tags (optional)</label>
                <div className="flex flex-wrap gap-2 mt-1">
                  {availableTags.map(tag => (
                    <button
                      key={tag}
                      onClick={() => handleTagToggle(tag)}
                      className={`px-2 py-1 text-xs rounded ${
                        selectedTags.includes(tag)
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted hover:bg-muted/80'
                      }`}
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>
              
              <div>
                <label className="text-xs font-medium">Comment (optional)</label>
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="What could be improved?"
                  className="w-full mt-1 p-2 text-xs border rounded bg-background"
                  rows={2}
                />
              </div>
              
              <div className="flex gap-2 justify-end">
                <button
                  onClick={handleCancel}
                  className="px-3 py-1 text-xs rounded hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSkip}
                  disabled={isSubmitting}
                  className="px-3 py-1 text-xs rounded hover:bg-muted"
                >
                  Skip
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={isSubmitting}
                  className="px-3 py-1 text-xs rounded bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  {isSubmitting ? 'Submitting...' : 'Submit'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
