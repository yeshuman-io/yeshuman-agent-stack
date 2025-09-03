import { CURRENT_CLIENT } from "@/constants";

interface TalentCoBrandProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const TalentCoBrand = ({ className = "", size = 'md' }: TalentCoBrandProps) => {
  if (CURRENT_CLIENT.name === 'TalentCo') {
    const sizeClasses = {
      sm: {
        letter: "w-5 h-5 text-sm font-semibold",
        co: "font-semibold text-sm"
      },
      md: {
        letter: "w-6 h-6 text-base font-semibold",
        co: "font-semibold text-base"
      },
      lg: {
        letter: "w-7 h-7 text-lg font-semibold",
        co: "font-semibold text-lg"
      }
    };

    const currentSize = sizeClasses[size];
    const letters = ['T', 'a', 'l', 'e', 'n', 't'];

    return (
      <div className={`flex items-baseline gap-0 ${className}`}>
        {letters.map((letter, index) => (
          <span
            key={index}
            className={`${currentSize.letter} text-white dark:text-gray-900 bg-blue-600 dark:bg-blue-500 flex items-center justify-center`}
          >
            {letter}
          </span>
        ))}
        <span className={`${currentSize.co} ml-0.5 text-blue-600 dark:text-blue-400`}>Co</span>
        <span className={`${currentSize.co} text-blue-600 dark:text-blue-400`}>!</span>
      </div>
    );
  }

  const sizeClasses = {
    sm: "font-semibold text-sm",
    md: "font-semibold text-base",
    lg: "font-semibold text-lg"
  };

  return (
    <span className={`truncate ${sizeClasses[size]} ${className}`}>
      {CURRENT_CLIENT.brand}
    </span>
  );
};

// Matrix-style Animated TalentCo Brand for use in animated titles
export const MatrixTalentCoBrand = ({ text, className = "", size = 'md' }: TalentCoBrandProps & { text: string }) => {
  if (CURRENT_CLIENT.name !== 'TalentCo') {
    const sizeClasses = {
      sm: "font-semibold text-sm",
      md: "font-semibold text-base",
      lg: "font-semibold text-lg"
    };

    return (
      <span className={`truncate ${sizeClasses[size]} ${className}`}>
        {text}
      </span>
    );
  }

  const sizeClasses = {
    sm: {
      letter: "w-5 h-5 text-sm font-semibold",
      co: "font-semibold text-sm",
      normal: "font-semibold text-sm"
    },
    md: {
      letter: "w-6 h-6 text-base font-semibold",
      co: "font-semibold text-base",
      normal: "font-semibold text-base"
    },
    lg: {
      letter: "w-7 h-7 text-lg font-semibold",
      co: "font-semibold text-lg",
      normal: "font-semibold text-lg"
    }
  };

  const currentSize = sizeClasses[size];
  const targetLetters = ['T', 'a', 'l', 'e', 'n', 't'];
  const coLetters = ['C', 'o', '!'];
  const textArray = text.split('');

  // Check if this is the final "TalentCo" state
  if (text === 'TalentCo') {
    return (
      <div className={`flex items-baseline gap-0 ${className}`}>
        {targetLetters.map((letter, index) => (
          <span
            key={index}
            className={`${currentSize.letter} text-white dark:text-gray-900 bg-blue-600 dark:bg-blue-500 flex items-center justify-center`}
          >
            {letter}
          </span>
        ))}
        <span className={`${currentSize.co} ml-0.5 text-blue-600 dark:text-blue-400`}>Co</span>
        <span className={`${currentSize.co} text-blue-600 dark:text-blue-400`}>!</span>
      </div>
    );
  }

  // Check if this is the final "TalentCo!" state
  if (text === 'TalentCo!') {
    return (
      <div className={`flex items-baseline gap-0 ${className}`}>
        {targetLetters.map((letter, index) => (
          <span
            key={index}
            className={`${currentSize.letter} text-white dark:text-gray-900 bg-blue-600 dark:bg-blue-500 flex items-center justify-center`}
          >
            {letter}
          </span>
        ))}
        <span className={`${currentSize.co} ml-0.5 text-blue-600 dark:text-blue-400`}>Co</span>
        <span className={`${currentSize.co} text-blue-600 dark:text-blue-400`}>!</span>
      </div>
    );
  }

  // Handle Matrix animation: each character position gets analyzed
  return (
    <div className={`flex items-baseline gap-0 ${className}`}>
      {textArray.map((char, index) => {
        // Handle spaces - keep them as plain text for proper spacing
        if (char === ' ') {
          return <span key={index}>&nbsp;</span>;
        }

        // Check if this position should be a TALENT letter (only for TalentCo)
        // We only apply blue boxes to TALENT letters when they're in their correct positions
        const isTalentLetter = targetLetters.includes(char);
        const shouldStyleAsTalent = isTalentLetter && (
          // For "TalentCo", check exact positions
          (text === 'TalentCo' && index < targetLetters.length && char === targetLetters[index]) ||
          // For other texts, only style if it matches the expected letter at that position
          (text !== 'TalentCo' && index < targetLetters.length && char === targetLetters[index])
        );

        if (shouldStyleAsTalent) {
          return (
            <span
              key={index}
              className={`${currentSize.letter} text-white dark:text-gray-900 bg-blue-600 dark:bg-blue-500 flex items-center justify-center`}
            >
              {char}
            </span>
          );
        }

        // Check if this character is "C" or "o" (blue colored letters, not boxed)
        const isCoLetter = coLetters.includes(char);
        if (isCoLetter) {
          return (
            <span key={index} className={`${currentSize.normal} text-blue-600 dark:text-blue-400`}>
              {char}
            </span>
          );
        }

        // Regular character
        return (
          <span key={index} className={currentSize.normal}>
            {char}
          </span>
        );
      })}
    </div>
  );
};
