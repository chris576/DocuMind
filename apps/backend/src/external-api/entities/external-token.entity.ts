import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn, UpdateDateColumn } from 'typeorm';

@Entity('external_tokens')
export class ExternalToken {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  userId: number;

  @Column()
  name: string;

  @Column({ unique: true })
  tokenHash: string;

  @Column()
  tokenPrefix: string;

  @Column('simple-array')
  scopes: string[];

  @Column({ default: true })
  isActive: boolean;

  @Column({ nullable: true })
  monthlyLimit: number;

  @Column({ type: 'timestamp', nullable: true })
  expiresAt: Date | null;

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;

  @Column({ type: 'timestamp', nullable: true })
  lastUsedAt: Date | null;
}
