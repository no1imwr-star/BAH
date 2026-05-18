import {
  pgTable,
  serial,
  integer,
  text,
  pgEnum,
  timestamp,
} from "drizzle-orm/pg-core";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { z } from "zod/v4";
import { carsTable } from "./cars";

export const orderStatusEnum = pgEnum("order_status", [
  "new",
  "in_progress",
  "done",
  "cancelled",
]);

export const ordersTable = pgTable("orders", {
  id: serial("id").primaryKey(),
  car_id: integer("car_id")
    .notNull()
    .references(() => carsTable.id, { onDelete: "restrict" }),
  customer_description: text("customer_description").notNull(),
  status: orderStatusEnum("status").notNull().default("new"),
  created_at: timestamp("created_at", { withTimezone: true })
    .notNull()
    .defaultNow(),
  updated_at: timestamp("updated_at", { withTimezone: true })
    .notNull()
    .defaultNow(),
});

export const insertOrderSchema = createInsertSchema(ordersTable, {
  car_id: z.number().int().positive(),
  customer_description: z.string().min(10).max(2000),
  status: z.enum(["new", "in_progress", "done", "cancelled"]).optional(),
}).omit({ id: true, created_at: true, updated_at: true });

export const selectOrderSchema = createSelectSchema(ordersTable);

export type InsertOrder = z.infer<typeof insertOrderSchema>;
export type Order = typeof ordersTable.$inferSelect;
export type OrderStatus = (typeof orderStatusEnum.enumValues)[number];
