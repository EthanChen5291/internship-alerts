import Anthropic from "@anthropic-ai/sdk";
import { zodOutputFormat } from "@anthropic-ai/sdk/helpers/zod";
import { z } from "zod";
import { config, log } from "./config.mjs";

/**
 * "Passive" = you sit somewhere (a desk, a booth, a monitor station), handle occasional
 * interruptions, and can do your own schoolwork the rest of the shift while being paid.
 */
const PASSIVE_TITLE = [
  [/front\s*desk|desk\s*(attendant|monitor|assistant|worker|staff|receptionist)|reception/i, 4],
  [/key\s*office|key\s*desk|grad(uate)?\s*center/i, 4],
  [/\b(building|facility|facilities|hall|lab|space|room|gallery|museum|weekend|night|evening|overnight)\s*(monitor|attendant|supervisor|assistant)\b/i, 4],
  [/\bmonitor\b|\battendant\b|\busher\b|\bgreeter\b/i, 3],
  [/info(rmation)?\s*desk|welcome\s*desk|circulation|check[-\s]?in|sign[-\s]?in|equipment\s*(checkout|desk|room)/i, 3],
  [/library|security\s*desk|lobby|access\s*control|door\s*(monitor|staff)/i, 2],
  [/office\s*(assistant|aide|worker)|student\s*(assistant|worker|aide)|help\s*desk/i, 1],
  [/proctor/i, 1],
];
const PASSIVE_TEXT = [
  [/(may|can|allowed to|welcome to|able to|encouraged to)\s+(study|do (school|home)work|do homework|work on (your|their|personal|academic|course)|read|bring (your )?(laptop|homework))/i, 5],
  [/downtime|down time|slow periods|quiet (periods|shifts|environment)|low[-\s]volume|when not busy|between (tasks|visitors|patrons)/i, 4],
  [/(sit|staff|stationed|cover|man|work) (at|behind) (the|a) (desk|front desk|table|booth|station)/i, 3],
  [/greet|answer (the )?(phone|phones|questions)|check(ing)? (ids|in|out)|sign (in|out) (visitors|guests|keys)|monitor(ing)? (the|a) (space|room|building|entrance|door|lobby|area)/i, 2],
  [/hand out|distribute (keys|equipment)|swipe|card access|open (and|\/) close|lock(ing)? up|unlock/i, 2],
  [/late[-\s]night|overnight|evening|weekend/i, 1],
];
const ACTIVE = [
  [/lifeguard|swim|coach|referee|official|instructor|trainer|fitness class/i, 6],
  [/dining|catering|cook|barista|cashier|server|dishwash|kitchen|food/i, 6],
  [/custodi|cleaning|janitor|setup crew|set-up|moving|mover|lift(ing)? (up to )?\d+|physical(ly)? demanding|on your feet|standing for/i, 5],
  [/driver|shuttle|delivery|courier|van/i, 5],
  [/tutor|teaching assistant|\bta\b|grader|grading|course assistant|note[-\s]?taker|peer (advisor|mentor|counselor)/i, 5],
  [/research (assistant|aide|intern)|lab (assistant|technician|tech)|data (entry|collection|analysis)|transcri|annotat|coding data/i, 4],
  [/childcare|child care|camp counselor|babysit|after[-\s]school/i, 5],
  [/phone[-\s]?a[-\s]?thon|caller|calling|fundrais|canvass|telefund|solicit/i, 5],
  [/tour guide|ambassador|guide|present(er|ations)|lead (tours|workshops|sessions)|facilitat/i, 4],
  [/developer|programmer|software|web design|graphic design|designer|video|photograph|editor|writer|content creat|social media|marketing/i, 4],
  [/fast[-\s]paced|high[-\s]volume|multi[-\s]task|constant|continuous|busy environment|heavy traffic/i, 3],
  [/sell|sales|vendor|retail|stock(ing)? shelves|inventory/i, 3],
  [/event (staff|setup|crew)|stagehand|production crew|technician/i, 2],
];

export function heuristicClassify(job, details = "") {
  const title = job.title || "";
  const text = [job.description, details, Object.values(job.raw || {}).join(" ")].join("\n");
  let score = 0;
  const reasons = [];
  const redFlags = [];
  for (const [re, w] of PASSIVE_TITLE) {
    const m = title.match(re);
    if (m) {
      score += w;
      reasons.push(`title mentions "${m[0]}"`);
    }
  }
  for (const [re, w] of PASSIVE_TEXT) {
    const m = text.match(re);
    if (m) {
      score += w;
      reasons.push(`posting says "${m[0].slice(0, 60)}"`);
    }
  }
  for (const [re, w] of ACTIVE) {
    const m = title.match(re) || text.match(re);
    if (m) {
      score -= title.match(re) ? w * 1.5 : w;
      redFlags.push(`mentions "${m[0].slice(0, 40)}"`);
    }
  }
  const verdict = score >= 4 ? "passive" : score >= 2 ? "maybe" : "not_passive";
  return {
    verdict,
    confidence: Math.min(0.9, Math.max(0.3, 0.5 + score / 20)),
    score,
    reasons: reasons.length ? reasons : ["no passive-job signals found"],
    redFlags,
    summary: verdict === "not_passive" ? "" : reasons.slice(0, 2).join("; "),
    source: "rules",
  };
}

const Verdict = z.object({
  verdict: z.enum(["passive", "maybe", "not_passive"]),
  confidence: z.number().min(0).max(1),
  summary: z.string().describe("One sentence, under 25 words, saying what the shift looks like."),
  reasons: z.array(z.string()).describe("Specific evidence from the posting."),
  red_flags: z.array(z.string()).describe("Anything that would keep the student from doing their own work on shift."),
});

const SYSTEM = `You screen Brown University student job postings for one student. They want jobs where they are paid to be present but mostly idle: sitting at a front desk, monitoring a building or key office, checking IDs occasionally, and otherwise free to do their own coursework on a laptop for most of the shift. Example of a perfect match: sitting at the Graduate Center key office front desk.

Classify each posting:
- "passive": the majority of a typical shift is unoccupied waiting time at a fixed station, and nothing in the posting forbids personal work.
- "maybe": plausibly low-activity, but the posting is vague, or it mixes desk time with real tasks.
- "not_passive": continuous work (tutoring, research, dining, lifeguarding, cleaning, driving, phone calling, teaching, design, coding, events, childcare) or explicit expectations of constant engagement.

Be skeptical of vague postings. Quote the posting in reasons. Keep summary short.`;

export async function classifyJob(job, details = "") {
  const rules = heuristicClassify(job, details);
  if (!config.anthropicKey) return rules;
  try {
    const client = new Anthropic();
    const posting = [
      `Title: ${job.title}`,
      job.department && `Department: ${job.department}`,
      job.pay && `Pay: ${job.pay}`,
      job.hours && `Hours: ${job.hours}`,
      job.location && `Location: ${job.location}`,
      job.description && `Description (list view): ${job.description}`,
      details && `Full posting text:\n${details}`,
      Object.keys(job.raw || {}).length && `Other fields: ${JSON.stringify(job.raw)}`,
    ]
      .filter(Boolean)
      .join("\n");
    const response = await client.messages.parse({
      model: "claude-opus-5",
      max_tokens: 2000,
      system: [{ type: "text", text: SYSTEM, cache_control: { type: "ephemeral" } }],
      output_config: { effort: "low", format: zodOutputFormat(Verdict) },
      messages: [{ role: "user", content: posting }],
    });
    if (response.stop_reason === "refusal" || !response.parsed_output) {
      log(`Claude gave no verdict for "${job.title}" (stop_reason=${response.stop_reason}); using rules`);
      return rules;
    }
    const p = response.parsed_output;
    return {
      verdict: p.verdict,
      confidence: p.confidence,
      score: rules.score,
      reasons: p.reasons,
      redFlags: p.red_flags,
      summary: p.summary,
      source: "claude",
      rulesVerdict: rules.verdict,
    };
  } catch (err) {
    if (err instanceof Anthropic.AuthenticationError) log("ANTHROPIC_API_KEY rejected; using rules");
    else if (err instanceof Anthropic.RateLimitError) log("Claude rate limited; using rules");
    else if (err instanceof Anthropic.APIError) log(`Claude API error ${err.status}: ${err.message}; using rules`);
    else log(`Claude call failed: ${err.message}; using rules`);
    return rules;
  }
}
