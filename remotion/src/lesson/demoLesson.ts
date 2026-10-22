import type {PremiumLessonProps} from './types';

/**
 * Preview content only: non-curricular UI data, without generated answers or
 * symbols. All actual mathematics remains authored and checked in Manim.
 */
export const demoLesson: PremiumLessonProps = {
  series: 'MATH CONCEPTS MADE EASY',
  level: 'GRADES 9–12  /  CONCEPT SERIES',
  title: 'Building Mathematical Intuition',
  tagline: 'Understand the idea. Follow the method. Build confidence.',
  introFrames: 60,
  outroFrames: 60,
  chapters: [
    {id: 'understand', stage: 'concept', title: 'Understand the Concept',
     learningGoal: 'See the core idea clearly before manipulating symbols.',
     durationInFrames: 105},
    {id: 'example', stage: 'worked_example', title: 'Follow a Worked Solution',
     learningGoal: 'Observe the verified reasoning, one stage at a time.',
     durationInFrames: 105},
    {id: 'practice', stage: 'practice', title: 'Practice the Method',
     learningGoal: 'Apply what you have learned, then check each step.',
     durationInFrames: 105},
    {id: 'review', stage: 'recap', title: 'Review and Remember',
     learningGoal: 'Connect the key ideas and prepare for your next topic.',
     durationInFrames: 105},
  ],
};
