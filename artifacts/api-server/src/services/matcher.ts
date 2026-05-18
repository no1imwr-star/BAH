import type { Service } from "@workspace/db";

export interface ScoredService {
  service: Service;
  score: number;
  matched_tags: string[];
}

/**
 * Normalize a Russian/English text string into a deduplicated set of tokens.
 * Lowercases, strips punctuation, splits on whitespace.
 */
export function tokenize(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .replace(/[^\p{L}\p{N}\s]/gu, " ")
      .split(/\s+/)
      .filter((t) => t.length >= 2),
  );
}

/**
 * Check if a tag matches any token using bidirectional substring:
 *   "тормоз" matches "тормоза", "тормозной" and vice-versa.
 * This handles Russian morphological variation without a stemmer.
 */
function tagMatchesTokens(tag: string, tokens: Set<string>): boolean {
  const normalizedTag = tag.toLowerCase();
  for (const token of tokens) {
    if (token.includes(normalizedTag) || normalizedTag.includes(token)) {
      return true;
    }
  }
  return false;
}

/**
 * Score a single service against a token set.
 * Returns score = number of distinct matching tags (0 if none).
 */
function scoreService(
  service: Service,
  tokens: Set<string>,
): { score: number; matched_tags: string[] } {
  const matched_tags: string[] = [];

  for (const tag of service.target_tags) {
    if (tagMatchesTokens(tag, tokens)) {
      matched_tags.push(tag);
    }
  }

  return { score: matched_tags.length, matched_tags };
}

/**
 * Pure function: rank services by relevance to the customer description.
 *
 * @param description - Free-text problem description from the customer
 * @param services    - Pre-fetched list of all candidate services
 * @param topN        - Maximum results to return (default 3)
 * @returns Scored services sorted by score DESC, duration ASC, capped at topN
 */
export function rankServices(
  description: string,
  services: Service[],
  topN = 3,
): ScoredService[] {
  const tokens = tokenize(description);

  const scored: ScoredService[] = services
    .map((service) => {
      const { score, matched_tags } = scoreService(service, tokens);
      return { service, score, matched_tags };
    })
    .filter((s) => s.score > 0);

  scored.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return Number(a.service.duration) - Number(b.service.duration);
  });

  return scored.slice(0, topN);
}
