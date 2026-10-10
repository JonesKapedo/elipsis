import { useState, useEffect } from "react"
import { CompanyBadge } from "@/components/company-badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import {
  AlertCircle,
  CheckCircle,
  XCircle,
  Eye,
  Loader2,
  FileText,
  Building2,
  Calendar,
  DollarSign,
  MapPin,
} from "lucide-react"

interface AdminRequest {
  id: number
  title: string
  description: string
  budget_range: string
  deadline: string | null
  location: string
  status: string
  verified_by_admin: number | null
  created_at: string
  organization: {
    id: number
    name: string
    industry: string
    company_size: "small" | "medium" | "big"
    city: string
    country: string
    contact_email: string
    contact_phone: string
  }
  client: {
    id: number
    name: string
    email: string
  }
  document_count: number
  bid_count: number
}

export default function AdminRequests() {
  const [requests, setRequests] = useState<AdminRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [selectedRequest, setSelectedRequest] = useState<AdminRequest | null>(null)
  const [actionDialog, setActionDialog] = useState<{
    type: "verify" | "publish" | "reject" | null
    notes: string
  }>({ type: null, notes: "" })
  const [processing, setProcessing] = useState(false)
  const [activeTab, setActiveTab] = useState("pending")

  useEffect(() => {
    fetchRequests(activeTab === "all" ? null : activeTab)
  }, [activeTab])

  const fetchRequests = async (status: string | null) => {
    setLoading(true)
    try {
      const url = status
        ? `/api/v1/admin/requests?status_filter=${status}`
        : "/api/v1/admin/requests"

      const response = await fetch(url)
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

  const handleAction = async (
    action: "verify" | "publish" | "reject",
    requestId: number
  ) => {
    setProcessing(true)
    setError("")

    try {
      let endpoint = `/api/v1/admin/requests/${requestId}/${action}`
      let body: any = {}

      if (action === "reject") {
        body.reason = actionDialog.notes || "Not specified"
      } else if (action === "verify") {
        body.notes = actionDialog.notes || null
      }

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || `Failed to ${action} request`)
      }

      setActionDialog({ type: null, notes: "" })
      setSelectedRequest(null)
      await fetchRequests(activeTab === "all" ? null : activeTab)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setProcessing(false)
    }
  }

  const renderRequestCard = (request: AdminRequest) => (
    <Card key={request.id} className="hover:shadow-md transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <CardTitle className="text-lg">{request.title}</CardTitle>
              <CompanyBadge size={request.organization.company_size} />
            </div>
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <Building2 className="h-3 w-3" />
                {request.organization.name}
              </span>
              <Badge variant={
                request.status === "pending" ? "secondary" :
                request.status === "verified" ? "default" :
                request.status === "published" ? "default" :
                "destructive"
              }>
                {request.status}
              </Badge>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground line-clamp-2 mb-4">
          {request.description}
        </p>

        <div className="grid grid-cols-2 gap-3 text-sm mb-4">
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
          <div className="flex items-center gap-2 text-muted-foreground">
            <FileText className="h-4 w-4" />
            {request.document_count} docs
          </div>
          {request.deadline && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Calendar className="h-4 w-4" />
              {new Date(request.deadline).toLocaleDateString()}
            </div>
          )}
        </div>

        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setSelectedRequest(request)}
          >
            <Eye className="h-4 w-4 mr-2" />
            View Details
          </Button>

          {request.status === "pending" && (
            <>
              <Button
                size="sm"
                onClick={() => {
                  setSelectedRequest(request)
                  setActionDialog({ type: "verify", notes: "" })
                }}
              >
                <CheckCircle className="h-4 w-4 mr-2" />
                Verify
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => {
                  setSelectedRequest(request)
                  setActionDialog({ type: "reject", notes: "" })
                }}
              >
                <XCircle className="h-4 w-4 mr-2" />
                Reject
              </Button>
            </>
          )}

          {request.status === "verified" && (
            <Button
              size="sm"
              onClick={() => {
                setSelectedRequest(request)
                setActionDialog({ type: "publish", notes: "" })
              }}
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Publish
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">Admin Panel</h1>
        <p className="text-muted-foreground">
          Manage and verify marketplace requests
        </p>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-6">
          <TabsTrigger value="pending">
            Pending ({requests.filter((r) => r.status === "pending").length})
          </TabsTrigger>
          <TabsTrigger value="verified">
            Verified ({requests.filter((r) => r.status === "verified").length})
          </TabsTrigger>
          <TabsTrigger value="published">Published</TabsTrigger>
          <TabsTrigger value="rejected">Rejected</TabsTrigger>
          <TabsTrigger value="all">All</TabsTrigger>
        </TabsList>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : (
          <TabsContent value={activeTab} className="space-y-4">
            {requests.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <p className="text-muted-foreground">
                    No {activeTab === "all" ? "" : activeTab} requests found
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {requests.map(renderRequestCard)}
              </div>
            )}
          </TabsContent>
        )}
      </Tabs>

      {/* Action Dialog */}
      <Dialog
        open={actionDialog.type !== null}
        onOpenChange={() => setActionDialog({ type: null, notes: "" })}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {actionDialog.type === "verify" && "Verify Request"}
              {actionDialog.type === "publish" && "Publish to Marketplace"}
              {actionDialog.type === "reject" && "Reject Request"}
            </DialogTitle>
            <DialogDescription>
              {actionDialog.type === "verify" &&
                "Mark this request as verified. You can publish it to the marketplace afterward."}
              {actionDialog.type === "publish" &&
                "This request will be visible to all subscribed bidders in the marketplace."}
              {actionDialog.type === "reject" &&
                "Please provide a reason for rejecting this request."}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="notes">
                {actionDialog.type === "reject" ? "Rejection Reason" : "Notes (Optional)"}
              </Label>
              <Textarea
                id="notes"
                value={actionDialog.notes}
                onChange={(e) =>
                  setActionDialog({ ...actionDialog, notes: e.target.value })
                }
                placeholder={
                  actionDialog.type === "reject"
                    ? "Explain why this request is being rejected..."
                    : "Add any internal notes..."
                }
                rows={4}
                required={actionDialog.type === "reject"}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setActionDialog({ type: null, notes: "" })}
            >
              Cancel
            </Button>
            <Button
              onClick={() =>
                selectedRequest &&
                actionDialog.type &&
                handleAction(actionDialog.type, selectedRequest.id)
              }
              disabled={
                processing ||
                (actionDialog.type === "reject" && !actionDialog.notes)
              }
            >
              {processing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  {actionDialog.type === "verify" && "Verify"}
                  {actionDialog.type === "publish" && "Publish"}
                  {actionDialog.type === "reject" && "Reject"}
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Request Details Dialog */}
      {selectedRequest && !actionDialog.type && (
        <Dialog
          open={!!selectedRequest}
          onOpenChange={() => setSelectedRequest(null)}
        >
          <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-2xl">
                {selectedRequest.title}
              </DialogTitle>
              <div className="flex items-center gap-2">
                <Badge>{selectedRequest.status}</Badge>
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
                  <h3 className="font-semibold mb-2">Client</h3>
                  <p className="text-sm">{selectedRequest.client.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {selectedRequest.client.email}
                  </p>
                </div>

                <div>
                  <h3 className="font-semibold mb-2">Organization</h3>
                  <p className="text-sm">{selectedRequest.organization.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {selectedRequest.organization.industry}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {selectedRequest.organization.contact_email}
                  </p>
                </div>

                <div>
                  <h3 className="font-semibold mb-2">Location</h3>
                  <p className="text-sm text-muted-foreground">
                    {selectedRequest.location}
                  </p>
                </div>

                {selectedRequest.budget_range && (
                  <div>
                    <h3 className="font-semibold mb-2">Budget</h3>
                    <p className="text-sm text-muted-foreground">
                      {selectedRequest.budget_range}
                    </p>
                  </div>
                )}
              </div>

              <Button onClick={() => setSelectedRequest(null)}>Close</Button>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
}
