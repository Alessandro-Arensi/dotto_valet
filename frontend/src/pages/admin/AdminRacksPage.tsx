import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Title,
  Stack,
  Paper,
  Group,
  Text,
  Anchor,
  Alert,
  Modal,
  Button,
  Textarea,
  SimpleGrid,
  Tooltip,
  Loader,
  Center,
  Badge,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconArrowLeft,
  IconInfoCircle,
  IconLockOpen,
  IconLock,
} from '@tabler/icons-react';

import { adminApi, RackDetail, SlotState } from '../../api/client';

const COLORS: Record<SlotState['status'], string> = {
  free: 'teal',
  checked_in: 'blue',
  blocked: 'red',
};

const LABELS: Record<SlotState['status'], string> = {
  free: 'Libero',
  checked_in: 'Bici parcheggiata',
  blocked: 'Bloccato',
};

export default function AdminRacksPage() {
  const { eventId } = useParams<{ eventId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [blockTarget, setBlockTarget] = useState<{
    rackId: string;
    slotNumber: number;
  } | null>(null);
  const [reason, setReason] = useState('');

  const { data: racks, isLoading } = useQuery({
    queryKey: ['admin', 'racks-detail', eventId],
    queryFn: () => adminApi.listRacksDetail(eventId!),
    enabled: !!eventId,
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['admin', 'racks-detail', eventId] });

  const blockMut = useMutation({
    mutationFn: (payload: { rackId: string; slot: number; reason: string }) =>
      adminApi.blockSlot(payload.rackId, payload.slot, payload.reason || undefined),
    onSuccess: () => {
      notifications.show({ message: 'Slot bloccato', color: 'green' });
      invalidate();
      setBlockTarget(null);
      setReason('');
    },
    onError: (e: Error) =>
      notifications.show({ message: e.message, color: 'red' }),
  });

  const releaseMut = useMutation({
    mutationFn: (payload: { rackId: string; slot: number }) =>
      adminApi.releaseSlot(payload.rackId, payload.slot),
    onSuccess: () => {
      notifications.show({ message: 'Slot liberato', color: 'green' });
      invalidate();
    },
    onError: (e: Error) =>
      notifications.show({ message: e.message, color: 'red' }),
  });

  const handleSlotClick = (rack: RackDetail, slot: SlotState) => {
    if (slot.status === 'checked_in') return;
    if (slot.status === 'blocked') {
      if (confirm(`Liberare slot ${slot.slot_number} (rast. ${rack.rack_number})?`)) {
        releaseMut.mutate({ rackId: rack.id, slot: slot.slot_number });
      }
      return;
    }
    setBlockTarget({ rackId: rack.id, slotNumber: slot.slot_number });
    setReason('');
  };

  if (isLoading) {
    return (
      <Center h="50vh">
        <Loader />
      </Center>
    );
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <Group>
          <Anchor
            onClick={() => navigate('/admin/events')}
            style={{ cursor: 'pointer' }}
          >
            <Group gap="xs">
              <IconArrowLeft size={16} />
              Eventi
            </Group>
          </Anchor>
          <Title order={2}>Rastrelliere</Title>
        </Group>
      </Group>

      <Alert icon={<IconInfoCircle size={16} />} color="blue">
        Le rastrelliere vengono create automaticamente quando definisci la
        capienza dell'evento (12 posti per rastrelliera). Click su uno slot
        libero per <strong>bloccarlo</strong> (bici fuori posto, bici cargo,
        manutenzione). Click su uno slot rosso per <strong>rilasciarlo</strong>.
      </Alert>

      <Group gap="md">
        <Legend color="teal" label="Libero" />
        <Legend color="blue" label="Parcheggiata" />
        <Legend color="red" label="Bloccato" />
      </Group>

      {(!racks || racks.length === 0) && (
        <Paper withBorder p="xl" radius="md" ta="center">
          <Text c="dimmed">
            Nessuna rastrelliera. Imposta la capienza dell'evento per
            generarle automaticamente.
          </Text>
        </Paper>
      )}

      {racks?.map((rack) => (
        <Paper key={rack.id} withBorder p="md" radius="md">
          <Group justify="space-between" mb="md">
            <Title order={4}>
              {rack.label || `Rastrelliera ${rack.rack_number}`}
            </Title>
            <Group gap="xs">
              <Badge variant="light" color="blue">
                {rack.states.filter((s) => s.status === 'checked_in').length} bici
              </Badge>
              <Badge variant="light" color="red">
                {rack.states.filter((s) => s.status === 'blocked').length} blocked
              </Badge>
              <Badge variant="light" color="teal">
                {rack.states.filter((s) => s.status === 'free').length} liberi
              </Badge>
            </Group>
          </Group>
          <SimpleGrid cols={{ base: 4, sm: 6, md: 12 }} spacing="xs">
            {rack.states.map((slot) => (
              <Tooltip
                key={slot.slot_number}
                label={
                  slot.status === 'checked_in'
                    ? `${LABELS[slot.status]} — ${slot.token_code}`
                    : slot.status === 'blocked'
                    ? `${LABELS[slot.status]}${slot.block_reason ? ` — ${slot.block_reason}` : ''}`
                    : LABELS[slot.status]
                }
                withArrow
              >
                <Paper
                  withBorder
                  p="xs"
                  radius="sm"
                  onClick={() => handleSlotClick(rack, slot)}
                  style={{
                    cursor:
                      slot.status === 'checked_in' ? 'not-allowed' : 'pointer',
                    borderColor: `var(--mantine-color-${COLORS[slot.status]}-6)`,
                    backgroundColor: `var(--mantine-color-${COLORS[slot.status]}-1)`,
                    textAlign: 'center',
                    userSelect: 'none',
                  }}
                >
                  <Text fw={600} size="sm">
                    {slot.slot_number}
                  </Text>
                  {slot.status === 'blocked' && (
                    <IconLock size={12} style={{ marginTop: 2 }} />
                  )}
                  {slot.status === 'free' && (
                    <IconLockOpen
                      size={12}
                      style={{ marginTop: 2, opacity: 0.3 }}
                    />
                  )}
                </Paper>
              </Tooltip>
            ))}
          </SimpleGrid>
        </Paper>
      ))}

      <Modal
        opened={!!blockTarget}
        onClose={() => {
          setBlockTarget(null);
          setReason('');
        }}
        title="Blocca slot"
      >
        <Stack>
          <Text size="sm">
            Stai per bloccare slot{' '}
            <strong>{blockTarget?.slotNumber}</strong>. Lo slot sarà saltato
            dall'auto-assegnazione finché non lo liberi.
          </Text>
          <Textarea
            label="Motivo (opzionale)"
            placeholder="es. Bici cargo, bici fuori posto, rastrelliera rotta"
            autosize
            minRows={2}
            value={reason}
            onChange={(e) => setReason(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button
              variant="light"
              onClick={() => {
                setBlockTarget(null);
                setReason('');
              }}
            >
              Annulla
            </Button>
            <Button
              color="red"
              loading={blockMut.isPending}
              onClick={() =>
                blockTarget &&
                blockMut.mutate({
                  rackId: blockTarget.rackId,
                  slot: blockTarget.slotNumber,
                  reason,
                })
              }
            >
              Blocca
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <Group gap="xs">
      <Paper
        withBorder
        w={18}
        h={18}
        style={{
          borderColor: `var(--mantine-color-${color}-6)`,
          backgroundColor: `var(--mantine-color-${color}-1)`,
        }}
      />
      <Text size="sm">{label}</Text>
    </Group>
  );
}
