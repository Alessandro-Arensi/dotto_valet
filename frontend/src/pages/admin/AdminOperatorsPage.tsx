import { useState } from 'react';
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
  PasswordInput,
  Switch,
  Badge,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { IconPlus, IconEdit, IconTrash } from '@tabler/icons-react';

import {
  adminApi,
  OperatorItem,
  OperatorCreate,
  OperatorUpdate,
} from '../../api/client';
import { useAuthStore } from '../../stores/authStore';

interface OperatorFormValues {
  name: string;
  phone: string;
  email: string;
  pin: string;
  is_admin: boolean;
  is_active: boolean;
}

export default function AdminOperatorsPage() {
  const queryClient = useQueryClient();
  const currentOperator = useAuthStore((s) => s.operator);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<OperatorItem | null>(null);

  const { data: operators, isLoading } = useQuery({
    queryKey: ['admin', 'operators'],
    queryFn: () => adminApi.listOperators(),
  });

  const form = useForm<OperatorFormValues>({
    initialValues: {
      name: '',
      phone: '',
      email: '',
      pin: '',
      is_admin: false,
      is_active: true,
    },
    validate: {
      name: (v) => (v.trim() ? null : 'Nome richiesto'),
      phone: (v) => (v.trim() ? null : 'Telefono richiesto'),
      pin: (v) => {
        if (editing && !v) return null;
        return /^\d{4,6}$/.test(v) ? null : 'PIN 4-6 cifre';
      },
    },
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['admin', 'operators'] });

  const createMut = useMutation({
    mutationFn: (payload: OperatorCreate) => adminApi.createOperator(payload),
    onSuccess: () => {
      notifications.show({ message: 'Operatore creato', color: 'green' });
      invalidate();
      closeModal();
    },
    onError: (e: Error) =>
      notifications.show({ message: e.message, color: 'red' }),
  });

  const updateMut = useMutation({
    mutationFn: (payload: { id: string; data: OperatorUpdate }) =>
      adminApi.updateOperator(payload.id, payload.data),
    onSuccess: () => {
      notifications.show({ message: 'Operatore aggiornato', color: 'green' });
      invalidate();
      closeModal();
    },
    onError: (e: Error) =>
      notifications.show({ message: e.message, color: 'red' }),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => adminApi.deleteOperator(id),
    onSuccess: () => {
      notifications.show({ message: 'Operatore disattivato', color: 'green' });
      invalidate();
    },
    onError: (e: Error) =>
      notifications.show({ message: e.message, color: 'red' }),
  });

  const openCreate = () => {
    form.reset();
    setEditing(null);
    setModalOpen(true);
  };

  const openEdit = (op: OperatorItem) => {
    setEditing(op);
    form.setValues({
      name: op.name,
      phone: op.phone || '',
      email: op.email || '',
      pin: '',
      is_admin: op.is_admin,
      is_active: op.is_active,
    });
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditing(null);
    form.reset();
  };

  const handleSubmit = (values: OperatorFormValues) => {
    if (editing) {
      const payload: OperatorUpdate = {
        name: values.name,
        phone: values.phone,
        email: values.email || undefined,
        is_admin: values.is_admin,
        is_active: values.is_active,
      };
      if (values.pin) payload.pin = values.pin;
      updateMut.mutate({ id: editing.id, data: payload });
    } else {
      const payload: OperatorCreate = {
        name: values.name,
        phone: values.phone,
        email: values.email || undefined,
        pin: values.pin,
        is_admin: values.is_admin,
        is_active: values.is_active,
      };
      createMut.mutate(payload);
    }
  };

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <Title order={2}>Operatori</Title>
        <Button leftSection={<IconPlus size={18} />} onClick={openCreate}>
          Nuovo operatore
        </Button>
      </Group>

      <Paper withBorder p="md" radius="md">
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Nome</Table.Th>
              <Table.Th>Telefono</Table.Th>
              <Table.Th>Ruolo</Table.Th>
              <Table.Th>Stato</Table.Th>
              <Table.Th ta="right">Azioni</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {!isLoading && operators?.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={5} ta="center">
                  Nessun operatore.
                </Table.Td>
              </Table.Tr>
            )}
            {operators?.map((op) => (
              <Table.Tr key={op.id}>
                <Table.Td>
                  {op.name}
                  {op.id === currentOperator?.id && (
                    <Badge ml="xs" size="xs" color="blue">
                      tu
                    </Badge>
                  )}
                </Table.Td>
                <Table.Td>{op.phone || '—'}</Table.Td>
                <Table.Td>
                  {op.is_admin ? (
                    <Badge color="grape">Admin</Badge>
                  ) : (
                    <Badge color="gray">Operatore</Badge>
                  )}
                </Table.Td>
                <Table.Td>
                  <Badge color={op.is_active ? 'green' : 'gray'}>
                    {op.is_active ? 'Attivo' : 'Disattivo'}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs" justify="flex-end">
                    <ActionIcon
                      variant="subtle"
                      title="Modifica"
                      onClick={() => openEdit(op)}
                    >
                      <IconEdit size={18} />
                    </ActionIcon>
                    <ActionIcon
                      variant="subtle"
                      color="red"
                      title="Disattiva"
                      disabled={op.id === currentOperator?.id}
                      onClick={() => {
                        if (confirm(`Disattivare "${op.name}"?`)) {
                          deleteMut.mutate(op.id);
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
        title={editing ? 'Modifica operatore' : 'Nuovo operatore'}
      >
        <form onSubmit={form.onSubmit(handleSubmit)}>
          <Stack>
            <TextInput
              label="Nome"
              required
              {...form.getInputProps('name')}
            />
            <TextInput
              label="Telefono"
              placeholder="+39 333 1234567"
              required
              {...form.getInputProps('phone')}
            />
            <TextInput
              label="Email"
              {...form.getInputProps('email')}
            />
            <PasswordInput
              label={editing ? 'PIN (lascia vuoto per non cambiare)' : 'PIN'}
              required={!editing}
              description="4-6 cifre"
              {...form.getInputProps('pin')}
            />
            <Switch
              label="Amministratore"
              {...form.getInputProps('is_admin', { type: 'checkbox' })}
            />
            <Switch
              label="Attivo"
              {...form.getInputProps('is_active', { type: 'checkbox' })}
            />
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
