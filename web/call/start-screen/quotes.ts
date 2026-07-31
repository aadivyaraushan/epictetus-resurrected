export type DiscourseQuote = {
  text: string;
  book: 1 | 2 | 3 | 4;
  chapter: number;
  citation: string;
};

function quote(
  text: string,
  book: DiscourseQuote["book"],
  chapter: number,
): DiscourseQuote {
  return {
    text,
    book,
    chapter,
    citation: `Discourses, Book ${book}, Chapter ${chapter}`,
  };
}

// Short passages copied from the committed George Long translation in
// corpus/source. Keeping this set explicit makes every front-page line
// attributable instead of cutting a random sentence out of a long paragraph.
export const DISCOURSES_QUOTES: readonly DiscourseQuote[] = [
  quote(
    "As then it was fit to be so, that which is best of all and supreme over all is the only thing which the gods have placed in our power, the right use of appearances; but all other things they have not placed in our power.",
    1,
    1,
  ),
  quote("Take care then, not to die without having been spectators of these things.", 1, 6),
  quote("to be instructed is this, to learn to wish that every thing may happen as it does.", 1, 12),
  quote("It is circumstances (difficulties) which show what men are.", 1, 24),
  quote("For death or pain is not formidable, but the fear of pain or death.", 2, 1),
  quote("Things themselves (materials) are indifferent; but the use of them is not indifferent.", 2, 5),
  quote(
    "For it is impossible for a man to begin to learn that which he thinks that he knows.",
    2,
    17,
  ),
  quote(
    "Generally then if you would make any thing a habit, do it; if you would not make it a habit, do not do it, but accustom yourself to do something else in place of it.",
    2,
    18,
  ),
  quote("The good man is invincible, for he does not enter the contest where he is not stronger.", 3, 6),
  quote(
    "Every thing which is difficult and dangerous is not suitable for practice; but that is suitable which conduces to the working out of that which is proposed to us.",
    3,
    12,
  ),
  quote("First say to yourself Who you wish to be: then do accordingly what you are doing;", 3, 23),
  quote("seek not the good in things external; seek it in yourselves: if you do not, you will not find it.", 3, 24),
  quote(
    "Not one then of the bad lives as he wishes; nor is he then free.",
    4,
    1,
  ),
  quote(
    "For to speak plainly, whatever the external thing may be, the value which we set upon it places us in subjection to others.",
    4,
    4,
  ),
  quote("There is only one way to happiness, and let this rule be ready both in the morning and during the day and by night:", 4, 4),
  quote(
    "But do you, until you know the opinion from which a man does each thing, neither praise nor blame the act.",
    4,
    8,
  ),
];

export function pickDiscourseQuote(randomValue: number): DiscourseQuote {
  if (!Number.isFinite(randomValue) || randomValue < 0 || randomValue >= 1) {
    return DISCOURSES_QUOTES[0];
  }
  return DISCOURSES_QUOTES[Math.floor(randomValue * DISCOURSES_QUOTES.length)];
}
