import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Title,
  Stack,
  Button,
  Paper,
  Table,
  Group,
  ActionIcon,
  Modal,
  TextInput,
  NumberInput,
  Switch,
  Badge,
  Textarea,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import {
  IconPlus,
  IconEdit,
  IconTrash,
  IconLayoutGrid,
} from '@tabler/icons-react';

import {
  adminApi,
  eventsApi,
  Event,
  EventCreate,
} from '../../api/client';

interface EventFormValues {
  name: string;
  description: string;
  location: string;
  start_date: string;
  end_date: string;
  checkin_opens_at: string;
  total_capacity: number;
  fast_mode_threshold: number;
  is_active: boolean;
}

function toIso(localInput: string): string | undefined {
  if (!localInput) return undefined;
  const d = new Date(localInput);
  return Number.isNaN(d.getTime()) ? undefined : d.toISOString();
}

function toLocalInput(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n: number) => String(n).padStart(2, '0');
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

export default function AdminEventsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Event | null>(null);

  const { data: events, isLoading } = useQuery({
    queryKey: ['admin', 'events'],
    queryFn: () => eventsApi.list(),
  });

  const form = useForm<EventFormValues>({
    initialValues: {
      name: '',
      description: '',
      location: '',
      start_date: '',
      end_date: '',
      checkin_opens_at: '',
      total_capacity: 50,
      fast_mode_threshold: 80,
      is_active: true,
    },
    validate: {
      name: (v) => (v.trim() ? null : 'Nome richiesto'),
      start_date: (v) => (v ? null : 'Data inizio richiesta'),
      total_capacity: (v) => (v > 0 ? null : 'Capienza > 0'),
    },
  });

  const createMut = useMutation({
    mutationFn: (payload: EventCreate) => adminApi.createEvent(payload),
    onSuccess: () => {
      notifications.show({ message: 'Evento creato', color: 'green' });
      queryClient.invalidateQueries({ queryKey: ['admin', 'events'] });
      queryClient.invalidateQueries({ queryKey: ['events'] });
      closeModal();
    },
    onError: (e: Error) =>
      notifications.show({ message: e.message, color: 'red' }),
  });

  const updateMut = useMutation({
    mutationFn: (payload: { id: string; data: Partial<EventCreate> & { is_active?: boolean } }) =>
      adminApi.updateEvent(payload.id, payload.data),
    onSuccess: () => {
      notifications.show({ message: 'Evento aggiornato', color: 'green' });
      queryClient.invalidateQueries({ queryKey: ['admin', 'events'] });
      queryClient.invalidateQueries({ queryKey: ['events'] });
      closeModal();
    },
    onError: (e: Error) =>
      notifications.show({ message: e.message, color: 'red' }),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => adminApi.deleteEvent(id),
    onSuccess: () => {
      notifications.show({ message: 'Evento disattivato', color: 'green' });
      queryClient.invalidateQueries({ queryKey: ['admin', 'events'] });
    },
    onError: (e: Error) =>
      notifications.show({ message: e.message, color: 'red' }),
  });

  const openCreate = () => {
    form.reset();
    setEditing(null);
    setModalOpen(true);
  };

  const openEdit = (event: Event) => {
    setEditing(event);
    form.setValues({
      name: event.name,
      description: event.description || '',
      location: event.location || '',
      start_date: toLocalInput(event.start_date),
      end_date: toLocalInput(event.end_date),
      checkin_opens_at: toLocalInput(event.checkin_opens_at),
      total_capacity: event.total_capacity,
      fast_mode_threshold: event.fast_mode_threshold ?? 80,
      is_active: event.is_active,
    });
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditing(null);
    form.reset();
  };

  const handleSubmit = (values: EventFormValues) => {
    const payload: EventCreate & { is_active?: boolean } = {
      name: values.name.trim(),
      description: values.description || undefined,
      location: values.location || undefined,
      start_date: toIso(values.start_date)!,
      end_date: toIso(values.end_date),
      checkin_opens_at: toIso(values.checkin_opens_at),
      total_capacity: values.total_capacity,
      fast_mode_threshold: values.fast_mode_threshold,
    };

    if (editing) {
      updateMut.mutate({
        id: editing.id,
        data: { ...payload, is_active: values.is_active },
      });
    } else {
      createMut.mutate(payload);
    }
  };

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <Title order={2}>Eventi</Title>
        <Button leftSection={<IconPlus size={18} />} onClick={openCreate}>
          Nuovo evento
        </Button>
      </Group>

      <Paper withBorder p="md" radius="md">
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Nome</Table.Th>
              <Table.Th>Slug</Table.Th>
              <Table.Th>Data</Table.Th>
              <Table.Th>Capienza</Table.Th>
              <Table.Th>Stato</Table.Th>
              <Table.Th ta="right">Azioni</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {!isLoading && events?.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={6} ta="center">
                  Nessun evento. Crea il primo.
                </Table.Td>
              </Table.Tr>
            )}
            {events?.map((event) => (
              <Table.Tr key={event.id}>
                <Table.Td>{event.name}</Table.Td>
                <Table.Td>
                  <code>{event.slug}</code>
                </Table.Td>
                <Table.Td>
                  {new Date(event.start_date).toLocaleDateString('it-IT')}
                </Table.Td>
                <Table.Td>{event.total_capacity}</Table.Td>
                <Table.Td>
                  <Badge color={event.is_active ? 'green' : 'gray'}>
                    {event.is_active ? 'Attivo' : 'Disattivo'}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs" justify="flex-end">
                    <ActionIcon
                      variant="subtle"
                      title="Gestisci rastrelliere"
                      onClick={() =>
                        navigate(`/admin/events/${event.id}/racks`)
                      }
                    >
                      <IconLayoutGrid size={18} />
                    </ActionIcon>
                    <ActionIcon
                      variant="subtle"
                      title="Modifica"
                      onClick={() => openEdit(event)}
                    >
                      <IconEdit size={18} />
                    </ActionIcon>
                    <ActionIcon
                      variant="subtle"
                      color="red"
                      title="Disattiva"
                      onClick={() => {
                        if (confirm(`Disattivare "${event.name}"?`)) {
                          deleteMut.mutate(event.id);
                        }
                      }}
                    >
                      <IconTrash size={18} />
                    </ActionIcon>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Paper>

      <Modal
        opened={modalOpen}
        onClose={closeModal}
        title={editing ? 'Modifica evento' : 'Nuovo evento'}
        size="lg"
      >
        <form onSubmit={form.onSubmit(handleSubmit)}>
          <Stack>
            <TextInput
              label="Nome evento"
              required
              description={
                editing
                  ? undefined
                  : 'Lo slug URL viene generato automaticamente dal nome.'
              }
              {...form.getInputProps('name')}
            />
            <Textarea
              label="Descrizione"
              autosize
              minRows={2}
              {...form.getInputProps('description')}
            />
            <TextInput label="Luogo" {...form.getInputProps('location')} />
            <Group grow>
              <TextInput
                type="datetime-local"
                label="Inizio"
                required
                {...form.getInputProps('start_date')}
              />
              <TextInput
                type="datetime-local"
                label="Fine"
                {...form.getInputProps('end_date')}
              />
            </Group>
            <TextInput
              type="datetime-local"
              label="Check-in apre alle"
              {...form.getInputProps('checkin_opens_at')}
            />
            <Group grow>
              <NumberInput
                label="Capienza totale"
                required
                min={1}
                {...form.getInputProps('total_capacity')}
              />
              <NumberInput
                label="Soglia fast-mode (%)"
                min={0}
                max={100}
                {...form.getInputProps('fast_mode_threshold')}
              />
            </Group>
            {editing && (
              <Switch
                label="Attivo"
                {...form.getInputProps('is_active', { type: 'checkbox' })}
              />
            )}
            <Group justify="flex-end">
              <Button variant="light" onClick={closeModal}>
                Annulla
              </Button>
              <Button
                type="submit"
                loading={createMut.isPending || updateMut.isPending}
              >
                {editing ? 'Salva' : 'Crea'}
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </Stack>
  );
}
