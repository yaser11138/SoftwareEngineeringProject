from django.db import transaction
from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .serializers import CombinedDiscussionTicketSerializer, TicketSerializer, DiscussionSerializer,\
    DiscussionListSerializer
from .models import Discussion
from .permissions import IsnotStaff, IsOwnerOrStuff


@extend_schema_view(
    list=extend_schema(description="if user is a staff member it gives all of discussions"
                                   "and if is not i just give use discussion"),
    create=extend_schema(description="Create a new discussion"),
    retrieve=extend_schema(
        description="Retrieve details of a discussion by ID",
        parameters=[OpenApiParameter('id', int, OpenApiParameter.PATH)]
    ),
    rate=extend_schema(
        description="Rate a discussion",
        parameters=[OpenApiParameter('id', int, OpenApiParameter.PATH)],
        request=CombinedDiscussionTicketSerializer,
        responses={status.HTTP_200_OK: {"detail": "The discussion rated"}}
    ),
    close=extend_schema(
        description="Close a discussion",
        parameters=[OpenApiParameter('id', int, OpenApiParameter.PATH)],
        responses={status.HTTP_200_OK: {"detail": "The discussion closed"}}
    ),
)
class DiscussionTicketViewSet(viewsets.ViewSet, PageNumberPagination):
    def get_permissions(self):
        if self.action == 'create' or self.action == 'rate':
            permission_classes = [IsAuthenticated, IsnotStaff]
        elif self.action == "retrive":
            permission_classes = [IsAuthenticated, IsOwnerOrStuff]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    serializer_class = CombinedDiscussionTicketSerializer

    def perform_create(self, serializer):
        serializer.save()

    @transaction.atomic()
    def create(self, request, *args, **kwargs):
        combined_serializer = self.get_serializer(data=request.data)
        combined_serializer.is_valid(raise_exception=True)

        user = request.user
        combined_serializer.validated_data['user'] = user

        self.perform_create(combined_serializer)

        data = combined_serializer.data['discussion']
        return Response(data={"status": "Discussion Opened", "data": data}, status=status.HTTP_201_CREATED)

    def list(self, request):
        if request.user.is_staff:
            queryset = Discussion.objects.all()
        else:
            queryset = Discussion.objects.filter(created_by=request.user)
        data = self.paginate_queryset(queryset, request)
        serializer = DiscussionListSerializer(instance=data, many=True)
        return self.get_paginated_response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            discussion = Discussion.objects.get(pk=pk)
        except Discussion.DoesNotExist:
            return Response(data={"detail": "Discussion not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = DiscussionSerializer(discussion)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        if 'rate' not in request.data:
            return Response(data={"error": "Rate hasn't been sent"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            discussion = Discussion.objects.get(pk=pk)
        except Discussion.DoesNotExist:
            return Response(data={"detail": "Discussion not found"}, status=status.HTTP_404_NOT_FOUND)
        discussion.rate = request.data.get("rate")
        discussion.save()
        return Response(data={"detail": "The discussion rated"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        try:
            discussion = Discussion.objects.get(pk=pk)
        except Discussion.DoesNotExist:
            return Response(data={"detail": "Discussion not found"}, status=status.HTTP_404_NOT_FOUND)
        discussion.is_terminated = True
        discussion.save()
        return Response(data={"detail": "The discussion closed"}, status=status.HTTP_200_OK)


class CreateTicket(APIView):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=TicketSerializer,
        description="Create a new ticket for for the discussion by ID",
        parameters=[OpenApiParameter('discussion_id', int, OpenApiParameter.PATH)],
    )
    def post(self, request, discussion_id):
        discussion = Discussion.objects.get(id=discussion_id)
        ticket_serializer = TicketSerializer(data=request.data)
        if ticket_serializer.is_valid():
            ticket_serializer.validated_data["discussion"] = discussion
            ticket_serializer.validated_data["user"] = request.user
            ticket_serializer.save()
            discussion.set_is_answered_vlaue(request.user)
            return Response(data={"ticket": ticket_serializer.data}, status=status.HTTP_201_CREATED)
        else:
            return Response(data={"error": ticket_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
