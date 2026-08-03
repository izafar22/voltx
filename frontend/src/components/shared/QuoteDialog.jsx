import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2, MessageCircle } from "lucide-react";

const segments = ["Residential", "Commercial", "Fleet", "Government", "Housing Society", "OEM / Private-label"];

export const QuoteDialog = ({ trigger, defaultProduct = "", title = "Request a Quote" }) => {
  const [open, setOpen] = useState(false);
  const [segment, setSegment] = useState("Residential");
  const { register, handleSubmit, reset, formState: { isSubmitting, errors } } = useForm();

  const onSubmit = async (data) => {
    try {
      const res = await api.post("/leads", { ...data, segment, product: defaultProduct });
      toast.success("Quote request sent!", { description: "A WhatsApp acknowledgment has been sent. Our team will reach out shortly." });
      reset(); setOpen(false);
      return res;
    } catch {
      toast.error("Could not submit. Please try again.");
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild data-testid="quote-dialog-trigger">{trigger}</DialogTrigger>
      <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto" data-testid="quote-dialog">
        <DialogHeader>
          <DialogTitle className="font-display text-2xl">{title}</DialogTitle>
          <DialogDescription>{defaultProduct ? `Enquiry for ${defaultProduct}` : "Tell us about your requirement and we'll get back within 24 hours."}</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>Full name</Label>
              <Input data-testid="quote-name" {...register("name", { required: true })} placeholder="Your name" className="h-11" />
              {errors.name && <p className="text-xs text-destructive">Required</p>}
            </div>
            <div className="space-y-1.5">
              <Label>Phone</Label>
              <Input data-testid="quote-phone" {...register("phone", { required: true })} placeholder="+91" className="h-11" />
              {errors.phone && <p className="text-xs text-destructive">Required</p>}
            </div>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>Email</Label>
              <Input data-testid="quote-email" type="email" {...register("email", { required: true })} placeholder="you@email.com" className="h-11" />
              {errors.email && <p className="text-xs text-destructive">Required</p>}
            </div>
            <div className="space-y-1.5">
              <Label>Company (optional)</Label>
              <Input data-testid="quote-company" {...register("company")} placeholder="Company" className="h-11" />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Customer segment</Label>
            <Select value={segment} onValueChange={setSegment}>
              <SelectTrigger data-testid="quote-segment" className="h-11"><SelectValue /></SelectTrigger>
              <SelectContent>
                {segments.map((s) => <SelectItem key={s} value={s} data-testid={`segment-${s}`}>{s}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Requirement</Label>
            <Textarea data-testid="quote-message" {...register("message", { required: true })} placeholder="Describe your requirement..." rows={3} />
            {errors.message && <p className="text-xs text-destructive">Required</p>}
          </div>
          <Button type="submit" disabled={isSubmitting} data-testid="quote-submit" className="w-full h-11 rounded-lg">
            {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <><MessageCircle className="h-4 w-4 mr-2" /> Send request</>}
          </Button>
          <p className="text-xs text-center text-muted-foreground">You'll receive a WhatsApp acknowledgment instantly.</p>
        </form>
      </DialogContent>
    </Dialog>
  );
};
