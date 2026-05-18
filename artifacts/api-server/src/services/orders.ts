import { eq } from "drizzle-orm";
import { db, carsTable, servicesTable, ordersTable } from "@workspace/db";
import type { InsertOrder } from "@workspace/db";
import { rankServices } from "./matcher";
import type { ScoredService } from "./matcher";

export interface SuggestResult {
  order_id: number;
  car: { id: number; brand: string; model: string; year: number };
  suggested_services: Array<{
    id: number;
    name: string;
    price: string;
    duration: number;
    matched_tags: string[];
    score: number;
  }>;
}

/**
 * Fetch a car by ID. Returns null if not found.
 */
export async function getCarById(carId: number) {
  const rows = await db
    .select()
    .from(carsTable)
    .where(eq(carsTable.id, carId))
    .limit(1);
  return rows[0] ?? null;
}

/**
 * Create a new order record and return the generated ID.
 */
export async function createOrder(data: InsertOrder): Promise<number> {
  const rows = await db
    .insert(ordersTable)
    .values(data)
    .returning({ id: ordersTable.id });
  return rows[0].id;
}

/**
 * Core orchestration for FR-01: suggest services for a new order.
 *
 * Steps:
 *   1. Validate car_id exists in DB — 404 if not
 *   2. Fetch all services from DB
 *   3. Run ranking algorithm against customer_description
 *   4. Persist the order with status "new"
 *   5. Return order_id + car info + top-N ranked services
 *
 * Throws CarNotFoundError if car_id is invalid.
 */
export async function suggestServicesForOrder(
  carId: number,
  customerDescription: string,
  topN = 3,
): Promise<SuggestResult> {
  const car = await getCarById(carId);
  if (!car) {
    throw new CarNotFoundError(carId);
  }

  const allServices = await db.select().from(servicesTable);

  const ranked: ScoredService[] = rankServices(
    customerDescription,
    allServices,
    topN,
  );

  const orderId = await createOrder({
    car_id: carId,
    customer_description: customerDescription,
    status: "new",
  });

  return {
    order_id: orderId,
    car: {
      id: car.id,
      brand: car.brand,
      model: car.model,
      year: car.year,
    },
    suggested_services: ranked.map(({ service, matched_tags, score }) => ({
      id: service.id,
      name: service.name,
      price: service.price,
      duration: service.duration,
      matched_tags,
      score,
    })),
  };
}

export class CarNotFoundError extends Error {
  constructor(public readonly carId: number) {
    super(`Car with id ${carId} not found`);
    this.name = "CarNotFoundError";
  }
}
