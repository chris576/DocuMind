import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn, ManyToOne, JoinColumn } from 'typeorm';
import { ExternalToken } from './external-token.entity';

@Entity('external_token_usage')
export class ExternalTokenUsage {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  tokenId: number;

  @ManyToOne(() => ExternalToken, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'tokenId' })
  token: ExternalToken;

  @Column()
  endpoint: string;

  @Column()
  method: string;

  @Column({ default: 0 })
  promptTokens: number;

  @Column({ default: 0 })
  completionTokens: number;

  @Column({ default: 0 })
  totalTokens: number;

  @Column()
  latencyMs: number;

  @Column({ nullable: true })
  sourceIp: string;

  @Column({ nullable: true })
  userAgent: string;

  @CreateDateColumn()
  timestamp: Date;
}
