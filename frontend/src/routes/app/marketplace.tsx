import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { CompanyBadge } from "@/components/company-badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  FileText,
  MapPin,
  Calendar,
  DollarSign,
  Building2,
  AlertCircle,
  Loader2,
} from "lucide-react"

interface MarketplaceRequest {
  id: number
  title: string
  description: string
  budget_range: string
  deadline: string | null
  location: string
  status: string
  created_at: string
  organization: {
    id: number
    name: string
    industry: string
    company_size: "small" | "medium" | "big"
    city: string
    country: string
    contact_email?: string
    contact_phone?: string
  }
  document_count: number
  bid_count: number
}

export default function Marketplace() {
  const navigate = useNavigate()
  const [requests, setRequests] = useState<MarketplaceRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [selectedRequest, setSelectedRequest] = useState<MarketplaceRequest | null>(null)
  const [showBidDialog, setShowBidDialog] = useState(false)
  const [bidForm, setBidForm] = useState({
    proposal: "",
    estimated_cost: "",
    timeline: "",
  })
  const [submittingBid, setSubmittingBid] = useState(false)

  useEffect(() => {
    fetchRequests()
  }, [])

  const fetchRequests = async () => {
    try {
      const response = await fetch("/api/v1/marketplace/requests")
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || "Failed to load requests")
      }

      setRequests(data.requests || [])
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleViewDetails = async (requestId: number) => {
    try {
      const response = await fetch(`/api/v1/marketplace/requests/${requestId}`)
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || "Failed to load request details")
      }

      setSelectedRequest(data)
    } catch (err: any) {
      setError(err.message)
    }
  }

  const handleSubmitBid = async () => {
    if (!selectedRequest) return

    setSubmittingBid(true)
    setError("")

    try {
      const response = await fetch(
        `/api/v1/marketplace/requests/${selectedRequest.id}/bid`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            proposal: bidForm.proposal,
            estimated_cost: parseFloat(bidForm.estimated_cost),
            timeline: bidForm.timeline,
          }),
        }
      )

      const data = await response.json()

      if (!response.ok) {
        if (response.status === 402) {
          throw new Error("Active subscription required to submit bids")
        }
        throw new Error(data.detail || "Failed to submit bid")
      }

      setShowBidDialog(false)
      setBidForm({ proposal: "", estimated_cost: "", timeline: "" })
      alert("Bid submitted successfully!")
      fetchRequests() // Refresh to update bid count
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSubmittingBid(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">Marketplace</h1>
        <p className="text-muted-foreground">
          Browse automation service requests from companies worldwide
        </p>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {requests.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Building2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No requests available</h3>
            <p className="text-muted-foreground">
              Check back soon for new automation service requests
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {requests.map((request) => (
            <Card
              key={request.id}
              className="cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => handleViewDetails(request.id)}
            >
              <CardHeader>
                <div className="flex items-start justify-between mb-2">
                  <CardTitle className="text-lg line-clamp-2">
                    {request.title}
                  </CardTitle>
                  <CompanyBadge size={request.organization.company_size} />
                </div>
                <CardDescription className="flex items-center gap-2">
                  <Building2 className="h-4 w-4" />
                  {request.organization.name}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground line-clamp-3">
                  {request.description}
                </p>

                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <MapPin className="h-4 w-4" />
                    {request.location}
                  </div>

                  {request.budget_range && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <DollarSign className="h-4 w-4" />
                      {request.budget_range}
                    </div>
                  )}

                  {request.deadline && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Calendar className="h-4 w-4" />
                      Due: {new Date(request.deadline).toLocaleDateString()}
                    </div>
                  )}

                  <div className="flex items-center gap-2 text-muted-foreground">
                    <FileText className="h-4 w-4" />
                    {request.document_count} documents
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2">
                  <Badge variant="secondary">{request.bid_count} bids</Badge>
                  <Badge>{request.status}</Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Request Details Dialog */}
      {selectedRequest && (
        <Dialog
          open={!!selectedRequest}
          onOpenChange={() => setSelectedRequest(null)}
        >
          <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <DialogTitle className="text-2xl mb-2">
                    {selectedRequest.title}
                  </DialogTitle>
                  <DialogDescription className="flex items-center gap-2">
                    <Building2 className="h-4 w-4" />
                    {selectedRequest.organization.name} •{" "}
                    {selectedRequest.organization.industry}
                  </DialogDescription>
                </div>
                <CompanyBadge size={selectedRequest.organization.company_size} />
              </div>
            </DialogHeader>

            <div className="space-y-6">
              <div>
                <h3 className="font-semibold mb-2">Description</h3>
                <p className="text-muted-foreground whitespace-pre-wrap">
                  {selectedRequest.description}
                </p>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <h3 className="font-semibold mb-2">Location</h3>
                  <p className="text-muted-foreground">{selectedRequest.location}</p>
                </div>

                {selectedRequest.budget_range && (
                  <div>
                    <h3 className="font-semibold mb-2">Budget Range</h3>
                    <p className="text-muted-foreground">
                      {selectedRequest.budget_range}
                    </p>
                  </div>
                )}

                {selectedRequest.deadline && (
                  <div>
                    <h3 className="font-semibold mb-2">Deadline</h3>
                    <p className="text-muted-foreground">
                      {new Date(selectedRequest.deadline).toLocaleDateString()}
                    </p>
                  </div>
                )}

                <div>
                  <h3 className="font-semibold mb-2">Status</h3>
                  <Badge>{selectedRequest.status}</Badge>
                </div>
              </div>

              {selectedRequest.organization.contact_email && (
                <div>
                  <h3 className="font-semibold mb-2">Contact Information</h3>
                  <p className="text-sm text-muted-foreground">
                    Email: {selectedRequest.organization.contact_email}
                  </p>
                  {selectedRequest.organization.contact_phone && (
                    <p className="text-sm text-muted-foreground">
                      Phone: {selectedRequest.organization.contact_phone}
                    </p>
                  )}
                </div>
              )}

              <div className="flex gap-2">
                <Button
                  className="flex-1"
                  onClick={() => {
                    setShowBidDialog(true)
                    setSelectedRequest(null)
                  }}
                >
                  Submit Bid
                </Button>
                <Button variant="outline" onClick={() => setSelectedRequest(null)}>
                  Close
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Bid Submission Dialog */}
      <Dialog open={showBidDialog} onOpenChange={setShowBidDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Submit Your Bid</DialogTitle>
            <DialogDescription>
              Provide your proposal and estimated costs
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="proposal">Your Proposal</Label>
              <Textarea
                id="proposal"
                placeholder="Describe your approach and methodology..."
                value={bidForm.proposal}
                onChange={(e) =>
                  setBidForm({ ...bidForm, proposal: e.target.value })
                }
                rows={6}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="cost">Estimated Cost (USD)</Label>
              <Input
                id="cost"
                type="number"
                placeholder="10000"
                value={bidForm.estimated_cost}
                onChange={(e) =>
                  setBidForm({ ...bidForm, estimated_cost: e.target.value })
                }
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="timeline">Estimated Timeline</Label>
              <Input
                id="timeline"
                placeholder="e.g., 2-3 weeks"
                value={bidForm.timeline}
                onChange={(e) =>
                  setBidForm({ ...bidForm, timeline: e.target.value })
                }
                required
              />
            </div>

            <div className="flex gap-2">
              <Button
                className="flex-1"
                onClick={handleSubmitBid}
                disabled={
                  submittingBid ||
                  !bidForm.proposal ||
                  !bidForm.estimated_cost ||
                  !bidForm.timeline
                }
              >
                {submittingBid ? "Submitting..." : "Submit Bid"}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setShowBidDialog(false)
                  setBidForm({ proposal: "", estimated_cost: "", timeline: "" })
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
