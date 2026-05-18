import { Router, type IRouter, type Request, type Response } from "express";
import { z, type ZodIssue } from "zod";
import { suggestServicesForOrder, CarNotFoundError } from "../services";
import { logger } from "../lib/logger";

const router: IRouter = Router();

const SuggestRequestSchema = z.object({
  car_id: z
    .number({ required_error: "car_id is required", invalid_type_error: "car_id must be a positive integer" })
    .int()
    .positive(),
  customer_description: z
    .string({ required_error: "customer_description is required", invalid_type_error: "customer_description must be a string" })
    .min(10, "customer_description must be at least 10 characters")
    .max(2000, "customer_description must not exceed 2000 characters")
    .transform((s: string) => s.trim()),
});

const SuggestResponseSchema = z.object({
  order_id: z.number().int(),
  car: z.object({
    id: z.number().int(),
    brand: z.string(),
    model: z.string(),
    year: z.number().int(),
  }),
  suggested_services: z.array(
    z.object({
      id: z.number().int(),
      name: z.string(),
      price: z.string(),
      duration: z.number().int(),
      matched_tags: z.array(z.string()),
      score: z.number().int(),
    }),
  ),
});

/**
 * POST /api/orders/suggest-services
 *
 * FR-01: Accept car_id + customer problem description,
 * rank matching services, persist a new order, return top-3 suggestions.
 *
 * SLA: response time ≤ 1500 ms (logged on every request for observability)
 *
 * Errors:
 *   400 — invalid / missing request fields (Zod parse failure)
 *   404 — car_id does not exist in the database
 *   500 — unexpected server error (safe message returned, full error logged)
 */
router.post(
  "/orders/suggest-services",
  async (req: Request, res: Response): Promise<void> => {
    const start = Date.now();

    const parsed = SuggestRequestSchema.safeParse(req.body);
    if (!parsed.success) {
      res.status(400).json({
        error: "Validation failed",
        details: parsed.error.issues.map((i: ZodIssue) => ({
          field: i.path.join("."),
          message: i.message,
        })),
      });
      return;
    }

    const { car_id, customer_description } = parsed.data;

    try {
      const result = await suggestServicesForOrder(car_id, customer_description);

      const elapsed = Date.now() - start;
      logger.info(
        { car_id, order_id: result.order_id, elapsed_ms: elapsed },
        "suggest-services: success",
      );

      if (elapsed > 1500) {
        logger.warn(
          { elapsed_ms: elapsed },
          "suggest-services: SLA breach (>1500 ms)",
        );
      }

      res.status(201).json(SuggestResponseSchema.parse(result));
    } catch (err) {
      if (err instanceof CarNotFoundError) {
        res.status(404).json({
          error: "Car not found",
          detail: `No car with id=${car_id} exists in the database.`,
        });
        return;
      }

      logger.error({ err, car_id }, "suggest-services: unexpected error");
      res.status(500).json({ error: "Internal server error" });
    }
  },
);

export default router;
