import React from "react";
import { CustomerSignInMethods } from "../components/CustomerSignInMethods";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components/ui/card";

export default {
  title: "Patterns/Customer Profile",
  component: CustomerSignInMethods,
  parameters: {
    docs: {
      description: {
        component:
          "Production sign-in method presentation with synthetic profile data. Verification actions are disabled in these stories.",
      },
    },
  },
};
const render = (args) => (
  <Card className="max-w-2xl">
    <CardHeader>
      <CardTitle>Contact and sign-in</CardTitle>
    </CardHeader>
    <CardContent>
      <CustomerSignInMethods {...args} busy />
    </CardContent>
  </Card>
);
export const GoogleOnly = {
  render,
  args: {
    user: {
      google_linked: true,
      email: "customer@example.com",
      phone_verified: false,
    },
  },
};
export const WhatsAppOnly = {
  render,
  args: {
    user: {
      google_linked: false,
      phone_verified: true,
      phone: "+919876543210",
    },
  },
};
export const BothLinked = {
  render,
  args: {
    user: {
      google_linked: true,
      email: "customer@example.com",
      phone_verified: true,
      phone: "+919876543210",
    },
  },
};
