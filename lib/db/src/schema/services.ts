import {
  pgTable,
  serial,
  varchar,
  numeric,
  smallint,
  text,
} from "drizzle-orm/pg-core";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const servicesTable = pgTable("services", {
  id: serial("id").primaryKey(),
  name: varchar("name", { length: 200 }).notNull(),
  price: numeric("price", { precision: 10, scale: 2 }).notNull(),
  duration: smallint("duration").notNull(),
  target_tags: text("target_tags").array().notNull().default([]),
});

export const insertServiceSchema = createInsertSchema(servicesTable, {
  name: z.string().min(1).max(200),
  price: z.string().regex(/^\d+(\.\d{1,2})?$/, "Must be a valid decimal price"),
  duration: z.number().int().min(1).max(600),
  target_tags: z.array(z.string().min(1).max(50)).min(1),
}).omit({ id: true });

export const selectServiceSchema = createSelectSchema(servicesTable);

export type InsertService = z.infer<typeof insertServiceSchema>;
export type Service = typeof servicesTable.$inferSelect;
