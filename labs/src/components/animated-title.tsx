import { useState, useRef, useCallback, useEffect } from 'react';
import { 
  titleVariations, 
  sarcasticVariations, 
  RANDOM_CHARS,
  ANIMATION_STEPS,
  STEP_DURATION,
  VARIATION_DISPLAY_TIME,
  SARCASTIC_DISPLAY_TIME,
  MIN_ANIMATION_DELAY,
  MAX_ANIMATION_DELAY,
  FIRST_ANIMATION_MIN_DELAY,
  FIRST_ANIMATION_MAX_DELAY
} from '../constants';
import type { AnimationTrigger } from '../types';

interface AnimatedTitleProps {
  onAnimationTrigger?: AnimationTrigger;
}

export const AnimatedTitle = ({ onAnimationTrigger }: AnimatedTitleProps) => {
  const [currentText, setCurrentText] = useState('Yes Human');
  const [displayText, setDisplayText] = useState('Yes Human');
  const [isAnimating, setIsAnimating] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  const animateTextTransition = (targetText: string) => {
    console.log(`🎭 Starting animation: "${currentText}" → "${targetText}"`);
    setIsAnimating(true);
    
    const maxLength = Math.max(currentText.length, targetText.length);
    let currentStep = 0;
    
    const animate = () => {
      if (currentStep < ANIMATION_STEPS) {
        // Randomization phase - show random characters
        const randomizedText = Array.from({ length: maxLength }, (_, i) => {
          const progress = currentStep / ANIMATION_STEPS;
          const shouldSettle = Math.random() < progress;
          
          if (shouldSettle && i < targetText.length) {
            return targetText[i];
          } else if (i < currentText.length && Math.random() < 0.3) {
            return currentText[i];
          } else {
            return RANDOM_CHARS[Math.floor(Math.random() * RANDOM_CHARS.length)];
          }
        }).join('').slice(0, maxLength);
        
        setDisplayText(randomizedText);
        currentStep++;
        setTimeout(animate, STEP_DURATION);
      } else {
        // Final settle to target text
        setDisplayText(targetText);
        setCurrentText(targetText);
        setIsAnimating(false);
        console.log(`✅ Animation complete: "${targetText}"`);
      }
    };
    
    animate();
  };
  
  // Regular animation cycle
  const triggerRegularAnimation = useCallback(() => {
    // Pick a random variation (excluding "Yes Human")
    const availableVariations = titleVariations.filter(text => text !== 'Yes Human');
    const randomVariation = availableVariations[Math.floor(Math.random() * availableVariations.length)];
    
    console.log(`🎬 Triggering regular animation cycle`);
    
    // Animate to the variation
    setTimeout(() => {
      animateTextTransition(randomVariation);
    }, 100);
    
    // Return to "Yes Human" after showing variation
    setTimeout(() => {
      if (randomVariation !== 'Yes Human') {
        animateTextTransition('Yes Human');
      }
    }, VARIATION_DISPLAY_TIME);
  }, []); // Removed currentText dependency

  // Sarcastic animation (for clicks and AI responses)
  const triggerSarcasticAnimation = useCallback(() => {
    const randomSarcastic = sarcasticVariations[Math.floor(Math.random() * sarcasticVariations.length)];
    
    console.log(`😈 Triggering sarcastic animation: "${randomSarcastic}"`);
    
    // Show sarcastic variation
    setTimeout(() => {
      animateTextTransition(randomSarcastic);
    }, 100);
    
    // Return to "Yes Human" after longer display
    setTimeout(() => {
      animateTextTransition('Yes Human');
    }, SARCASTIC_DISPLAY_TIME);
  }, []);

  // Handle click event
  const handleTitleClick = () => {
    console.log('🖱️ Title clicked - triggering sarcastic response');
    triggerSarcasticAnimation();
  };

  // Function to schedule next animation
  const scheduleNextAnimation = useCallback(() => {
    // Clear any existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    
    const randomDelay = MIN_ANIMATION_DELAY + Math.random() * (MAX_ANIMATION_DELAY - MIN_ANIMATION_DELAY);
    console.log(`⏰ Next animation scheduled in ${Math.round(randomDelay/1000)}s`);
    
    timeoutRef.current = setTimeout(() => {
      triggerRegularAnimation();
      scheduleNextAnimation(); // Schedule the next one
    }, randomDelay);
  }, [triggerRegularAnimation]);

  // Separate effect for exposing trigger function
  useEffect(() => {
    if (onAnimationTrigger) {
      onAnimationTrigger(triggerSarcasticAnimation);
    }
  }, [onAnimationTrigger, triggerSarcasticAnimation]);

  // Main animation scheduling effect (runs only once)
  useEffect(() => {
    // First animation after random delay
    const firstDelay = FIRST_ANIMATION_MIN_DELAY + Math.random() * (FIRST_ANIMATION_MAX_DELAY - FIRST_ANIMATION_MIN_DELAY);
    console.log(`🚀 First animation will trigger after ${Math.round(firstDelay/1000)}s`);
    
    const firstTimeout = setTimeout(() => {
      console.log(`🚀 First animation trigger executing now`);
      triggerRegularAnimation();
      scheduleNextAnimation(); // Start the recurring schedule
    }, firstDelay);
    
    return () => {
      clearTimeout(firstTimeout);
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []); // No dependencies - runs only once on mount
  
  return (
    <h1 
      className={`text-xl font-semibold transition-all duration-300 font-mono cursor-pointer hover:opacity-75 ${
        isAnimating ? 'opacity-90 scale-[0.98]' : 'opacity-100 scale-100'
      }`}
      style={{ minWidth: '200px' }} // Prevent layout shift during animation
      onClick={handleTitleClick}
      title="Click me for attitude 😈"
    >
      {displayText}
    </h1>
  );
};
